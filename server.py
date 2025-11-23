import os
import re
import json
from datetime import datetime
import time
import uuid
import base64
import requests
import zipfile
from pathlib import Path
from kling import ImageGenerator, MultiImage2Image
from werkzeug.utils import secure_filename
from urllib.parse import urlparse, unquote
import string
from flask import Flask, request, jsonify
from qwen import QwenChat
from flask_cors import CORS
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app,
     origins=["http://localhost:5173"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=True,
     max_age=86400  # OPTIONS 结果缓存 24h
)

# 定义后端对外访问的 base 地址（用于返回绝对 URL）
BACKEND_BASE = "http://127.0.0.1:5000"
video_tasks = {}  # task_id → {status, video_url, error, start_time}
video_executor = ThreadPoolExecutor(max_workers=2)  # 视频生成 GPU 密集，严格限制并发

def dataurl_to_file(dataurl, filename=None):
    """
    dataurl example: "data:image/jpeg;base64,/9j/4AAQ.."
    返回写好的文件路径（字符串）
    """
    print(f"Attempting to convert data URL to file: {dataurl[:100]}...")  # 打印前100个字符
    m = re.match(r"data:(image/\w+);base64,(.*)", dataurl, re.S)
    if not m:
        print("Invalid data URL format")
        raise ValueError("不是合法的 data URL")
    
    mime, b64 = m.groups()
    ext = mime.split('/')[-1]
    
    if not filename:
        filename = f"{uuid.uuid4().hex}.{ext}"
    
    out_path = GENERATED_DIR / filename
    
    # 检查路径是否存在，不存在则创建
    if not GENERATED_DIR.exists():
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64))
        print(f"File successfully written: {out_path}")
    except Exception as e:
        print(f"Error writing file: {e}")
        raise
    
    return str(out_path)


def sanitize_filename_from_url(url):
    """改为：用 UUID v4 + 原扩展名，完全避免路径问题"""
    # 解析扩展名（安全兜底）
    parsed = urlparse(url)
    path = unquote(parsed.path)
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if not ext or ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        ext = '.jpg'
    # 生成唯一文件名
    safe_name = f"{uuid.uuid4().hex}{ext}"
    return safe_name

def download_to_generated(url, filename=None):
    try:
        if not filename:
            filename = sanitize_filename_from_url(url)
        out_path = GENERATED_DIR / filename
        # 使用 stream=True 分块写入，避免大文件一次性占内存
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        # 返回绝对 URL，便于前端直接访问
        return f"{BACKEND_BASE}/static/generated/{out_path.name}"
    except Exception as e:
        print("下载失败:", e)
        return None

from concurrent.futures import ThreadPoolExecutor, as_completed

@app.route('/generate-images', methods=['POST'])
def generate_images():
    """
    接收前端传来的 sentence_pairs，对 prompt != null 的项调用 MultiImage2Image 生成图片。
    每个 item 的 photo 字段为 base64 字符串数组（参考图），取前4张作为 subject_imgs，
    第1张同时作为 style_img（传入 style_img 参数）。
    【修改】使用 ThreadPoolExecutor 实现并行生成，提升效率。
    """
    try:
        payload = request.get_json()
        pairs = payload.get("sentence_pairs", [])
        if not pairs:
            return jsonify({"error": "no sentence_pairs"}), 400

        # 共享实例与认证（✅ 避免每任务重复初始化）
        ig = MultiImage2Image()
        token = ig._encode_jwt_token()
        AUTHORIZATION = f"Bearer {token}"
        HEADERS = {"Content-Type": "application/json", "Authorization": AUTHORIZATION}

        def extract_base64(dataurl_or_b64: str) -> str:
            """内嵌辅助函数：提取 base64 字符串"""
            if dataurl_or_b64.startswith("data:image"):
                try:
                    return dataurl_or_b64.split(",", 1)[1]
                except IndexError:
                    raise ValueError("Invalid data URL format")
            return dataurl_or_b64

        def process_single_pair(item):
            """处理单个 sentence_pair，返回结果 dict（含 index）"""
            idx = item.get("index", 0)  # 兼容无 index 字段
            prompt = item.get("prompt")

            if not prompt:
                return {
                    "index": idx,
                    "prompt": None,
                    "generated_urls": [],
                    "note": "no prompt"
                }

            photo_list = item.get("photo", [])
            if not isinstance(photo_list, list):
                photo_list = []

            if len(photo_list) < 2:
                return {
                    "index": idx,
                    "prompt": prompt,
                    "generated_urls": [],
                    "error": "subject_imgs must contain at least 2 images"
                }

            subject_photo_list = photo_list[:4]
            try:
                subject_imgs = [
                    {"subject_image": extract_base64(img)} for img in subject_photo_list
                ]
                style_img_b64 = extract_base64(subject_photo_list[0])
            except Exception as e:
                return {
                    "index": idx,
                    "prompt": prompt,
                    "generated_urls": [],
                    "error": f"photo preprocessing failed: {str(e)}"
                }

            # 调用 Kling API（独立任务）
            try:
                task_result = ig.run(
                    headers=HEADERS,
                    prompt=prompt,
                    subject_imgs=subject_imgs,
                    style_img=style_img_b64,
                    model_name="kling-v2",
                    n=1,
                    aspect_ratio="3:4",
                    max_wait=300,
                    interval=5
                )
            except Exception as e:
                return {
                    "index": idx,
                    "prompt": prompt,
                    "generated_urls": [],
                    "error": f"kling run failed: {str(e)}"
                }

            # 解析结果 → 本地 URL
            generated_urls = []
            try:
                data = task_result.get("data", {})
                imgs = data.get("task_result", {}).get("images", []) or []
                for im in imgs:
                    remote_url = im.get("url")
                    if remote_url:
                        local_url = download_to_generated(remote_url)
                        if local_url:
                            generated_urls.append(local_url)
                        else:
                            # fallback: 尝试直接下载保存
                            try:
                                resp = requests.get(remote_url, timeout=30)
                                resp.raise_for_status()
                                mime = resp.headers.get('content-type', 'image/jpeg')
                                ext = '.jpg' if 'jpeg' in mime.lower() else '.png' if 'png' in mime.lower() else '.jpg'
                                b64 = base64.b64encode(resp.content).decode()
                                dataurl = f"data:{mime};base64,{b64}"
                                fallback_path = dataurl_to_file(dataurl, filename=f"fallback_{uuid.uuid4().hex}{ext}")
                                fallback_url = f"{BACKEND_BASE}/static/generated/{Path(fallback_path).name}"
                                generated_urls.append(fallback_url)
                            except Exception as ex:
                                print(f"❌ fallback failed for {remote_url}: {ex}")
                    else:
                        b64 = im.get("b64") or im.get("base64")
                        if b64:
                            try:
                                fn = f"{uuid.uuid4().hex}.jpg"
                                out_path = GENERATED_DIR / fn
                                out_path.write_bytes(base64.b64decode(b64))
                                generated_urls.append(f"{BACKEND_BASE}/static/generated/{out_path.name}")
                            except Exception as ex:
                                print(f"Base64 save failed:", ex)
            except Exception as e:
                print(f"Parse result failed for index {idx}:", e)

            return {
                "index": idx,
                "prompt": prompt,
                "generated_urls": generated_urls
            }

        # 🔥 并行处理：控制并发数 ≤5（Kling 实测安全上限）
        results = [None] * len(pairs)
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(process_single_pair, item): i
                for i, item in enumerate(pairs)
            }

            # 收集结果（保持原始顺序）
            for future in as_completed(future_to_index):
                try:
                    result = future.result()
                    orig_idx = future_to_index[future]  # 在 pairs 中的原始位置（用于保序）
                    results[orig_idx] = result
                except Exception as e:
                    # 极端异常兜底（如线程崩溃）
                    print(f"⚠️ Thread crashed for item {future_to_index[future]}:", e)
                    # 可选：填充空结果
                    results[future_to_index[future]] = {
                        "index": future_to_index[future],
                        "prompt": None,
                        "generated_urls": [],
                        "error": f"thread exception: {str(e)}"
                    }

        # 移除 None（若未来出现未填充）
        results = [r for r in results if r is not None]

        return jsonify({"results": results})

    except Exception as e:
        print("generate-images exception:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

# Qwen API Key 和 Base URL 配置
API_KEY = "sk-fbdc82229399417892a94c001b5ea873" # 替换成自己的key
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

qwen = QwenChat()
@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    try:
        data = request.get_json()
        photos = data['photos']
        narratives = data['narratives']

        # 构建系统提示词
        system_prompt = """
            你是一名专业的记忆研究助理。
            你的任务是：根据用户提供的照片和文字描述，生成帮助用户回忆的开放性问题。
            要求：
            1. 严格输出 JSON 数组。
            2. 数组中每个元素是对象，必须包含字段：
            - text: 问题内容
            - answer: 空字符串
            - answered: false
            - showInput: false
            3. 不要生成回答，只输出问题。
            4. 语言使用中文。
            5. 提问的维度可以包括时间、地点、人物、场景、情感等。
            示例：
            [
            {"text": "请描述这张照片中的人物是谁？", "answer": "", "answered": false, "showInput": false},
            {"text": "照片中的场景对你意味着什么？", "answer": "", "answered": false, "showInput": false}
            ]
            """
        prompt = f"""
            用户提供的文字内容如下：
            {narratives}
            请结合上述内容和用户上传的照片生成一系列问题，严格遵守 system_prompt 中的 JSON 输出格式。
            """

        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=photos,
            model="qwen-vl-max",
            enable_image_input=True
        )
        print('生成的问题：', result)
        # 将字符串解析成 Python list
        try:
            # ✅ [修改] 增强 JSON 解析
            match = re.search(r'\[.*\]', str(result), re.DOTALL)
            if match:
                questions = json.loads(match.group(0))
            else:
                questions = []
        except json.JSONDecodeError:
            questions = []  # 避免报错
            print("⚠️ JSON 解析失败:", result)

        return jsonify({"questions": questions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ [新增] Stage 3 整合文本 (App.vue 需要)
@app.route('/integrate-text', methods=['POST'])
def integrate_text():
    try:
        data = request.get_json()
        narrative = data.get('narrative', '')
        qa_pairs = data.get('qa_pairs', [])
        
        # 将 Q&A 转换为易读的文本块
        qa_text = "\n".join([
            f"Q: {qa['question']}\nA: {qa['answer']}" 
            for qa in qa_pairs
        ])

        system_prompt = """
        你是一个专业的叙事作家。
        你的任务是：将用户的第一版口述（Narrative）和后续的补充问答（Q&A）整合成一段*单一、连贯、流畅*的叙事文本。
        要求：
        1. 必须融合 Narrative 和 Q&A 的所有信息。
        2. 消除重复内容。
        3. 以第一人称（"我"）进行叙述。
        4. 风格自然，就像在讲故事。
        5. *只*输出整合后的完整文本，不要任何额外解释。
        """
        
        prompt = f"""
        请整合以下两部分内容：

        ---
        第一版口述 (Narrative):
        {narrative}
        ---
        补充问答 (Q&A):
        {qa_text}
        ---
        
        请严格按照 system_prompt 的要求，将它们融合成一段*单一、完整*的叙事文本。
        """

        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=[],
            model="qwen-vl-max", # 或 "qwen-max"
            enable_image_input=False
        )
        
        result_text = str(result).strip()
        print("整合后的文本 (Stage 3):", result_text)
        
        return jsonify({"integrated_text": result_text})

    except Exception as e:
        print("⚠️ (Stage 3) /integrate-text 异常:", e)
        return jsonify({"error": str(e)}), 500

# ✅ [修改] Stage 4 获取引导问题 (根据新逻辑)
@app.route('/generate-stage4-questions', methods=['POST'])
def generate_stage4_questions():
    try:
        data = request.get_json()
        original_photos = data.get('original_photos', []) # base64
        ai_photos_urls = data.get('ai_photos_urls', [])   # urls
        # suggestion = data.get('suggestion', '') # ✅ [移除] 不再需要 suggestion

        # Qwen-VL 可以混合处理 base64 data URLs 和 http URLs
        all_images = original_photos + ai_photos_urls

        system_prompt = """
            你是一名专业的视觉迭代助理。
            你的任务是：根据用户提供的*原始照片*和*当前AI生成的照片*，生成 3-5 个引导性问题，帮助用户*补充叙事细节*。
            要求：
            1. 严格输出 JSON 数组。
            2. 数组中每个元素是对象，必须包含字段：
            - text: 问题内容
            - answer: 空字符串
            - answered: false
            - showInput: false
            3. 问题应聚焦于*叙事*，例如询问关于 "AI 生成的图像" 中新出现的 "元素"、"氛围" 或 "动作" 的相关回忆。
            4. 语言使用中文。
            示例：
            [
            {"text": "AI 生成的这张图片中，光线看起来很柔和，这让您想起了当时具体的时间或天气吗？", "answer": "", "answered": false, "showInput": false},
            {"text": "这张 AI 图片额外生成了一些背景细节，这是否让您回忆起关于这个地点的更多故事？", "answer": "", "answered": false, "showInput": false}
            ]
            """
        
        prompt = f"""
            (已附上 原始照片 和 当前AI生成的照片)
            请仔细对比原始照片和 AI 生成的照片，针对 AI 生成图片中的新内容或氛围，提问 3-5 个具体问题，帮助用户*回忆*更多相关的*故事*或*细节*。
            严格遵守 system_prompt 中的 JSON 输出格式。
            """

        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=all_images,
            model="qwen-vl-max",
            enable_image_input=True
        )
        print('生成的问题 (Stage 4)：', result)
        
        try:
            match = re.search(r'\[.*\]', str(result), re.DOTALL)
            if match:
                questions = json.loads(match.group(0))
            else:
                questions = []
        except json.JSONDecodeError:
            questions = []
            print("⚠️ (Stage 4) JSON 解析失败:", result)

        return jsonify({"questions": questions})
    
    except Exception as e:
        print("⚠️ (Stage 4) /generate-stage4-questions 异常:", e)
        return jsonify({"error": str(e)}), 500

# ✅ [新增] Stage 4 更新文本
@app.route('/update-text', methods=['POST'])
def update_text():
    try:
        data = request.get_json()
        current_narrative = data.get('current_narrative', '')
        new_qa_pairs = data.get('new_qa_pairs', [])
        
        if not new_qa_pairs:
             return jsonify({"updated_text": ""}) # 如果没有新回答，返回空

        qa_text = "\n".join([
            f"Q: {qa['question']}\nA: {qa['answer']}" 
            for qa in new_qa_pairs
        ])

        system_prompt = """
        你是一个叙事编辑。
        你的任务是：根据用户的新一轮补充问答（Q&A），生成一段*新的、补充性*的叙事文本。
        要求：
        1. *只*根据 Q&A 的内容进行总结和扩写。
        2. 风格自然，第一人称（"我"）。
        3. *只*输出新生成的补充段落。不要重复用户之前说过的话 (在 current_narrative 中)，不要包含任何 Q&A 之外的信息。
        4. 输出必须是连贯的段落，而不是 Q&A 列表。
        """
        
        prompt = f"""
        这是用户已有的叙述 (供参考，不要重复)：
        ---
        {current_narrative}
        ---
        
        这是用户刚刚补充的回答 (请整合这部分)：
        ---
        {qa_text}
        ---
        
        请严格按照 system_prompt 的要求，将*补充的回答*整合成一段*新的*补充叙述。
        """

        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=[],
            model="qwen-vl-max", # 或 "qwen-max"
            enable_image_input=False
        )
        
        result_text = str(result).strip()
        print("更新的文本 (Stage 4):", result_text)
        
        return jsonify({"updated_text": result_text})

    except Exception as e:
        print("⚠️ (Stage 4) /update-text 异常:", e)
        return jsonify({"error": str(e)}), 500

    
@app.route('/generate-prompts', methods=['POST'])
def generate_prompts():
    try:
        data = request.get_json()

        photos = data['photos']  # 图片路径列表
        print("📩 收到的 图片 数据：", len(photos))
        narratives = data['narrative']  # 用户输入叙述文本
        print("📩 收到的 文本 数据：", narratives)

        # Step 1：调用 Qwen 分句+生成 prompt
        system_prompt_1 = """
        你是一个专业的叙事视觉设计助手，擅长将叙述性文本转化为具备时空真实感的分镜式视觉场景序列。

        请严格按以下规则处理输入文本：

        1. 【按视觉场景切分】  
        以“视觉场景的实质性变化”为唯一切分依据，包括：  
        - 主体/人物更换  
        - 空间/环境切换（如教室→操场）  
        - 时间跃迁（如清晨→黄昏、1995年→2003年）  
        - 关键动作或事件转折  
        - 情绪/氛围的显著转变  
        → 连续描述同一时空内细节、心理或静态状态的语句，必须合并为一句。

        2. 【时空背景显式嵌入】  
        每个prompt必须清晰包含**时代特征**与**地域文化语境**，例如：  
        - 时间：1990年代、改革开放初期、千禧年前夕  
        - 地点：中国北方军校校园、华东小城老街、复旦大学邯郸校区  
        - 社会特征：绿皮火车、搪瓷杯、手写黑板报、军绿书包、CRT显示器等时代符号  
        → 严禁出现时代错位元素（如90年代出现智能手机、玻璃幕墙高楼）或文化错配（如中国军校出现外国学生群像，除非原文明确提及）。

        3. 【prompt生成规范】  
        每条prompt约20字，聚焦可绘制内容，必须包含：  
        - 主体（谁/什么）  
        - 关键动作或状态  
        - 具体环境（含时代+地域特征）  
        - 光影/天气/氛围（增强叙事感）  
        → 避免抽象词（如‘怀念’‘奋斗’），改用可视符号（如‘泛黄的笔记本摊在木课桌上’）。

        4. 【叙事连贯性】  
        所有prompt应构成逻辑连贯、情绪递进的视觉序列，服务于整体故事意图。

        严格输出 JSON 数组格式：
        [
            {"sentence": "一句叙述", "prompt": "一句中文prompt"},
            ...
        ]
        """
        prompt_1 = f"""
        用户提供的叙述文本如下：
        {narratives}
        请严格遵守 system_prompt 的要求输出 JSON。
        """

        response_1 = qwen.get_response(
            prompt=prompt_1,
            system_prompt=system_prompt_1,
            image_path_list=[],
            model="qwen-vl-max",
            enable_image_input=False
        )
        # 确保提取出文本
        if isinstance(response_1, dict) and "output" in response_1:
            text_output = response_1["output"].get("text", "")
        else:
            text_output = str(response_1)

        try:
            # ✅ [修改] 增强 JSON 解析
            match = re.search(r'\[.*\]', text_output, re.DOTALL)
            if match:
                qwen_sentences = json.loads(match.group(0))
            else:
                qwen_sentences = []
        except Exception as e:
            print("⚠️ (generate-prompts) JSON 解析失败:", e, text_output)
            qwen_sentences = [{"sentence": narratives, "prompt": "no prompt"}]
        
        if not qwen_sentences:
            print("⚠️ (generate-prompts) Qwen 未返回有效句子，降级处理")
            qwen_sentences = [{"sentence": narratives, "prompt": narratives}] # 降级处理

        print("📝 Qwen 分句+prompt 结果：", qwen_sentences)


        # Step 2: 对每张照片寻找语义最接近的句子（photo→sentence）
        matched_indices = set()
        sentence_pairs = []

        for photo_idx, photo in enumerate(photos):
            # 拼接所有句子到一个 prompt，一次性请求 Qwen 计算所有相似度
            all_sentences_text = "\n".join(
                [f"{i+1}. {item['sentence']}" for i, item in enumerate(qwen_sentences)]
            )

            match_prompt = f"""
        你是一个图像语义匹配助手。
        下面有一张图片，以及若干文字描述（编号1~{len(qwen_sentences)}）。
        请你对每个文字描述与图片的语义相关性打分（0~100分）。
        输出严格为 JSON 数组格式，如：[{{"index": 1, "score": 78}}, ...]
        文字列表：
        {all_sentences_text}
            """

            match_response = qwen.get_response(
                prompt=match_prompt,
                system_prompt="仅输出JSON数组，不要解释。",
                image_path_list=[photo],
                model="qwen-vl-max",
                enable_image_input=True
            )

            try:
                # ✅ [修改] 增强 JSON 解析
                match = re.search(r'\[.*\]', str(match_response), re.DOTALL)
                if match:
                    scores = json.loads(match.group(0))
                else:
                    scores = []
            except:
                scores = []
                print("⚠️ (generate-prompts) 匹配得分 JSON 解析失败:", match_response)

            # 找出最高分的句子
            if scores:
                best_match = max(scores, key=lambda x: x.get("score", 0))
                best_idx = best_match.get("index", 0) - 1  # 转成从0开始的索引
                best_score = best_match.get("score", 0)
            else:
                best_idx, best_score = None, 0
            
            print(f"Photo {photo_idx} 最佳匹配: index {best_idx}, score {best_score}")

            # (修改) 阈值调低，并确保 best_idx 有效
            if best_score > 50 and (best_idx is not None) and (0 <= best_idx < len(qwen_sentences)) and (best_idx not in matched_indices):
                matched_indices.add(best_idx)
                sentence_pairs.append({
                    "index": best_idx, # (新增) 保持原始索引
                    "photo": photo,
                    "sentence": qwen_sentences[best_idx]["sentence"],
                    "prompt": None # 有原图，不需要 prompt
                })
            else:
                # 照片没有匹配到任何句子，或匹配得分过低，或句子已被匹配
                sentence_pairs.append({
                    "index": photo_idx, # (修改) 使用 photo_idx 作为临时索引
                    "photo": photo,
                    "sentence": None,
                    "prompt": None
                })

        # Step 3: 把剩余未匹配的句子添加为需生成图的 prompt
        for idx, item in enumerate(qwen_sentences):
            if idx not in matched_indices:
                sentence_pairs.append({
                    "index": idx, # (新增) 保持原始索引
                    "photo": None,
                    "sentence": item["sentence"],
                    "prompt": item["prompt"]
                })
        
        print("✅ (generate-prompts) 最终配对结果:", sentence_pairs)
        return jsonify({"sentence_pairs": sentence_pairs})


    except Exception as e:
        print("⚠️ (generate-prompts) /generate-prompts 异常:", e)
        return jsonify({"error": str(e)}), 500

# UPLOADS_DIR = Path(__file__).parent / "static" / "uploads"
# UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/upload-photo', methods=['POST'])
def upload_photo():
    try:
        if 'photo' not in request.files:
            return jsonify({"success": False, "message": "No photo provided"}), 400
        file = request.files['photo']
        if file.filename == '':
            return jsonify({"success": False, "message": "Empty filename"}), 400
        if file:
            # 安全文件名
            safe_name = secure_filename(file.filename)
            if not safe_name:
                safe_name = f"{uuid.uuid4().hex}.jpg"
            # 添加时间戳防重
            name = f"{int(time.time())}_{safe_name}"
            filepath = UPLOADS_DIR / name
            file.save(filepath)
            url = f"/static/uploads/{name}"
            return jsonify({"success": True, "url": url})
    except Exception as e:
        print("Upload error:", e)
        return jsonify({"success": False, "message": str(e)}), 500


LOGS_DIR = Path(__file__).parent / "experiment_logs"
LOGS_DIR.mkdir(exist_ok=True)


@app.route('/save-experiment-log', methods=['POST'])
def save_experiment_log():
    try:
        data = request.get_json()
        log_data = data.get("log", {})

        user_id = str(log_data.get("userId", "anonymous")).replace("/", "_").replace("\\", "_")
        session_id = str(log_data.get("sessionId", "unknown")).replace("/", "_").replace("\\", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建用户/会话专属目录
        session_dir = LOGS_DIR / user_id / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # 1️⃣ 先保存精简版 JSON（不含图像数据）
        # 移除大字段（若存在 base64），保留 URL 和 meta
        clean_log = {
            k: v for k, v in log_data.items()
            if k not in ["originalPhotosBase64", "aiPhotosBase64"]
        }

        json_path = session_dir / f"log_{ts}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(clean_log, f, ensure_ascii=False, indent=2)

        print(f"✅ Log JSON saved: {json_path.relative_to(LOGS_DIR)}")

        # 2️⃣ 打包 assets.zip（含所有原始 & AI 图像）
        zip_path = session_dir / f"assets_{ts}.zip"
        assets_count = 0

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # -- 原始照片 --
                orig_urls = log_data.get("originalPhotoUrls", [])
                for i, url in enumerate(orig_urls):
                    local_path = _resolve_local_path(url, UPLOADS_DIR)
                    if local_path and local_path.exists():
                        arcname = f"original_{i+1:02d}{local_path.suffix}"
                        zf.write(local_path, arcname)
                        assets_count += 1
                    else:
                        print(f"⚠️ Original photo #{i+1} not found: {url}")

                # -- AI 生成照片 --
                ai_urls = log_data.get("aiPhotoUrls", [])
                ai_meta = log_data.get("aiPhotoMeta", [])
                for i, url in enumerate(ai_urls):
                    local_path = _resolve_local_path(url, GENERATED_DIR)
                    if local_path and local_path.exists():
                        # 尝试从 meta 取标签，否则用 index
                        label = f"ai_{i+1:02d}"
                        if i < len(ai_meta):
                            iter_label = ai_meta[i].get("iterationLabel", "").replace(" ", "_")
                            prompt_snippet = (ai_meta[i].get("prompt", "")[:30].replace("/", "_").replace("\\", "_") or "no_prompt")
                            label = f"{label}_{iter_label}_{prompt_snippet}"
                        arcname = f"{label}{local_path.suffix}"
                        zf.write(local_path, arcname)
                        assets_count += 1
                    else:
                        print(f"⚠️ AI photo #{i+1} not found: {url}")

        except Exception as e:
            print(f"❌ assets.zip creation failed: {e}")
            zip_path.unlink(missing_ok=True)  # 删除残缺 zip
            zip_path = None

        # 3️⃣ 返回成功响应
        response = {
            "success": True,
            "logJson": json_path.name,
            "assetsZip": zip_path.name if zip_path else None,
            "imageCount": assets_count
        }

        print(f"✅ Experiment session saved: user={user_id}, session={session_id}, images={assets_count}")
        return jsonify(response)

    except Exception as e:
        print("❌ save-experiment-log error:", e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

UPLOADS_DIR = Path(__file__).parent / "static" / "uploads"
GENERATED_DIR = Path(__file__).parent / "static" / "generated"

def _resolve_local_path(url: str, base_dirs: list[Path] = None) -> Path | None:
    """
    支持从 uploads / generated 任一目录按文件名查找
    base_dirs 默认为 [UPLOADS_DIR, GENERATED_DIR]
    【修复】新增 .jpg / .png 扩展名互查 fallback
    """
    if not url or not isinstance(url, str):
        return None
    if url.startswith(("blob:", "data:")):
        return None

    if base_dirs is None:
        base_dirs = [UPLOADS_DIR, GENERATED_DIR]

    # 提取原始文件名（含扩展名）
    try:
        fname = os.path.basename(urlparse(unquote(url)).path)
        if not fname or '.' not in fname:
            return None
        stem, orig_ext = os.path.splitext(fname)
        orig_ext = orig_ext.lower()
    except Exception as e:
        print(f"[WARN] 解析 URL {url} 出错: {e}")
        return None

    # 第一轮：原扩展名精确匹配
    for base in base_dirs:
        candidate = base / fname
        if candidate.is_file():
            print(f"✅ 路径解析成功 (精确匹配): {url} → {candidate}")
            return candidate

    # 第二轮：扩展名 fallback —— .png ⇄ .jpg 互查
    ext_fallbacks = []
    if orig_ext == '.png':
        ext_fallbacks = ['.jpg', '.jpeg']
    elif orig_ext in ['.jpg', '.jpeg']:
        ext_fallbacks = ['.png']
    else:
        ext_fallbacks = ['.jpg', '.png', '.jpeg']

    for ext in ext_fallbacks:
        alt_fname = stem + ext
        for base in base_dirs:
            candidate = base / alt_fname
            if candidate.is_file():
                print(f"✅ 路径解析成功 (扩展名 fallback): {url} → {candidate} | 原名: {fname}")
                return candidate

    print(f"❌ 无法解析 URL → 本地路径: {url}，尝试文件名: {fname} 及 fallback 扩展名均失败")
    return None

def url_to_local(url: str) -> Path | None:
    if url.startswith("http://127.0.0.1:5000/") or url.startswith("/"):
        path_part = urlparse(url).path.lstrip("/")
        if path_part.startswith("static/"):
            rel = path_part[len("static/"):]
            # 根据目录名判断应查 uploads 还是 generated
            if rel.startswith("uploads/"):
                return UPLOADS_DIR / rel[len("uploads/"):]
            elif rel.startswith("generated/"):
                return GENERATED_DIR / rel[len("generated/"):]
    # fallback: 可能是纯文件名
    fname = os.path.basename(urlparse(url).path)
    for base in [UPLOADS_DIR, GENERATED_DIR]:
        p = base / fname
        if p.exists():
            return p
    return None

@app.route('/generate-video', methods=['POST'])
def generate_video():
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        data = request.get_json()
        photo_urls = data.get("photos", [])
        raw_prompts = data.get("prompts", [])

        # ===== 参数标准化 =====
        if isinstance(raw_prompts, str):
            try:
                prompts = json.loads(raw_prompts)
            except:
                prompts = [raw_prompts]
        elif isinstance(raw_prompts, list):
            prompts = raw_prompts
        else:
            prompts = [str(raw_prompts)]

        if len(photo_urls) < 2:
            return jsonify({"error": "photos 至少需要 2 张（AABB 格式）"}), 400
        if len(photo_urls) % 2 != 0:
            return jsonify({"error": "photos 长度必须为偶数（AABB...）"}), 400

        # ✅ 分配唯一 task_id
        task_id = str(uuid.uuid4())
        video_tasks[task_id] = {
            "status": "pending",
            "videoUrl": None,
            "error": None,
            "start_time": time.time()
        }

        # ✅ 异步提交任务（非阻塞）
        video_executor.submit(_run_video_generation_task, task_id, photo_urls, prompts)

        # ✅ 立即返回
        return jsonify({
            "task_id": task_id,
            "status": "submitted",
            "message": "视频生成任务已提交，请轮询 /video-status/<task_id>"
        })

    except Exception as e:
        print("❌ /generate-video submit error:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _run_video_generation_task(task_id: str, photo_urls: list, prompts: list):
    """独立任务函数：执行视频生成全流程"""
    temp_dir = None
    try:
        # 更新状态
        video_tasks[task_id]["status"] = "downloading"

        # === 下载图片 ===
        temp_dir = Path(tempfile.mkdtemp())
        local_paths = []

        for url in photo_urls:
            local_path = _resolve_local_path(url, [UPLOADS_DIR, GENERATED_DIR])
            if not local_path or not local_path.exists():
                fname = sanitize_filename_from_url(url)
                local_path = temp_dir / fname
                try:
                    resp = requests.get(url, stream=True, timeout=30)
                    resp.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                except Exception as e:
                    raise Exception(f"下载 {url} 失败: {e}")

            # 强制转为 .jpg（兼容即梦）
            if local_path.suffix.lower() not in ['.jpg', '.jpeg']:
                try:
                    from PIL import Image
                    img = Image.open(local_path).convert("RGB")
                    jpg_path = local_path.with_suffix('.jpg')
                    img.save(jpg_path, "JPEG", quality=95)
                    if jpg_path != local_path:
                        local_path.unlink(missing_ok=True)
                        local_path = jpg_path
                except Exception as e:
                    print(f"[Warn] 图片格式转换失败 {local_path}: {e}")

            local_paths.append(str(local_path))

        # === 调用 generate.py ===
        video_tasks[task_id]["status"] = "generating"
        output_filename = f"final_{uuid.uuid4().hex}.mp4"
        output_path = GENERATED_DIR / output_filename

        cmd = [
            "python", "generate.py",
            "--photos", *local_paths,
            "--prompts", *prompts,
            "--output", str(output_path)
        ]

        print(f"[Task {task_id[:6]}] 🔍 执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1200,
            cwd=os.path.dirname(__file__)
        )

        if result.returncode != 0:
            stderr_msg = (result.stderr or result.stdout)[:500]
            raise Exception(f"generate.py 失败: {stderr_msg}")

        if not output_path.exists():
            raise Exception("视频文件未生成（路径不存在）")

        video_url = f"{BACKEND_BASE}/static/generated/{output_filename}"
        print(f"[Task {task_id[:6]}] ✅ 视频生成成功: {video_url}")

        # ✅ 更新状态
        video_tasks[task_id].update({
            "status": "success",
            "videoUrl": video_url,
            "end_time": time.time()
        })

    except Exception as e:
        error_msg = str(e)
        print(f"[Task {task_id[:6]}] ❌ 视频生成失败:", error_msg)
        import traceback
        traceback.print_exc()
        video_tasks[task_id].update({
            "status": "failed",
            "error": error_msg,
            "end_time": time.time()
        })

    finally:
        # ✅ 确保清理
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"[Task {task_id[:6]}] 清理失败: {e}")

@app.route('/video-status/<task_id>', methods=['GET'])
def video_status(task_id: str):
    task = video_tasks.get(task_id)
    if not task:
        return jsonify({"error": "task_id 不存在或已过期"}), 404

    # 可选：自动清除超时任务（如 >1 小时）
    now = time.time()
    if task.get("start_time") and now - task["start_time"] > 3600:
        video_tasks.pop(task_id, None)
        return jsonify({"error": "任务已超时清理"}), 410

    return jsonify({
        "task_id": task_id,
        "status": task["status"],  # pending → downloading → generating → success/failed
        "videoUrl": task.get("videoUrl"),
        "error": task.get("error"),
        "elapsed": now - task["start_time"] if "start_time" in task else None
    })

# 调用Qwen为视频生成prompts
@app.route('/refine-prompt', methods=['POST'])
def refine_prompt():
    """
    新增字段：
      type: "static" | "transition"
    输入：
      static:  sentence = 当前画面描述；prev/next 用于氛围衔接
      transition: sentence + next_sentence = 起止画面；prev/post 用于过渡上下文
    """
    try:
        data = request.get_json()
        prompt_type = data.get("type", "transition")  # static / transition
        sentence = data.get("sentence", "").strip()
        next_sent = data.get("next_sentence", "").strip()
        prev_sent = data.get("prev_sentence", "").strip()
        post_sent = data.get("post_sentence", "").strip()

        if prompt_type == "static":
            system_prompt = """
            你是一名专业影视分镜师，擅长将回忆转化为视频生成指令。
            当前任务：为**单张静态照片**生成视频 prompt，表现「微动态」而非剧烈变化。
            要求：
            1. **必须包含**：人物微动作（如眨眼、嘴角微扬、衣角轻摆）、镜头微运动（缓慢推进/环绕）、氛围风格；
            2. 控制在 10~20 字；
            3. 避免「回忆」「时光」等抽象词，聚焦**画面内可观测元素**；
            4. 仅输出 prompt，无标点结尾，无解释。
            示例：
            - 微笑凝视远方，发丝轻扬，镜头缓慢推进，暖色调胶片感
            - 老人轻抚相框，手指微颤，浅景深，柔光怀旧风
            """
            content = f"画面描述：{sentence}"
            if prev_sent or next_sent:
                content += f"\n上下文：前{('「'+prev_sent+'」') if prev_sent else '无'}，后{('「'+next_sent+'」') if next_sent else '无'}"
            content += "\n请生成静帧微动视频 prompt："

        else:  # transition
            system_prompt = """
            你是一名专业影视分镜师，擅长设计镜头过渡。
            当前任务：为**两张照片之间的切换**生成视频 prompt，表现自然、有叙事逻辑的过渡。
            要求：
            1. **必须包含**：过渡主体（如人物转身、视线移动）、镜头运动（平移/旋转/缩放）、过渡氛围；
            2. 明确起止画面核心元素（如“从微笑→凝望”“从屋前→屋内”）；
            3. 控制在 12~25 字；
            4. 仅输出 prompt，无标点结尾，无解释。
            示例：
            - 人物缓缓转身，镜头平移跟随，从微笑切换为凝望远方
            - 镜头拉远展现全景，从老屋门廊自然过渡到院中桂花树
            """
            content = f"起始画面：{sentence}\n结束画面：{next_sent}"
            if prev_sent or post_sent:
                content += f"\n前情：{prev_sent}" if prev_sent else ""
                content += f"\n后续：{post_sent}" if post_sent else ""
            content += "\n请生成画面过渡视频 prompt："

        result = qwen.get_response(
            prompt=content,
            system_prompt=system_prompt,
            model="qwen-max",
            enable_image_input=False
        )
        refined = str(result).strip().rstrip("。！？,.，")
        # 安全兜底
        if not refined or len(refined) > 50:
            refined = sentence[:12] + ('过渡' if prompt_type == 'transition' else '静帧')

        return jsonify({"prompt": refined})

    except Exception as e:
        print("❌ /refine-prompt error:", e)
        return jsonify({"error": str(e)}), 500    


def download_to_generated(url, filename=None):
    try:
        if not filename:
            filename = sanitize_filename_from_url(url)
        out_path = GENERATED_DIR / filename
        print(f"📥 尝试下载: {url} → {out_path}")
        
        with requests.get(url, stream=True, timeout=30) as r:
            print(f"↔️ 响应状态: {r.status_code}, Content-Type: {r.headers.get('content-type', 'unknown')}")
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"✅ 文件已保存: {out_path}")
        return f"{BACKEND_BASE}/static/generated/{out_path.name}"
    except Exception as e:
        print(f"❌ 下载失败 (url={url}): {e}")
        return None

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)