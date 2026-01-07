import os
import re
import json
from datetime import datetime
import time
import uuid
import base64
import requests
import zipfile
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
from pathlib import Path
from typing import Optional, List  
from qwenVLLM import analyze_images

app = Flask(__name__)
CORS(app,
     origins=["http://localhost:5173"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=True,
     max_age=86400
)

# === 配置与初始化 ===
BACKEND_BASE = "http://127.0.0.1:5000"
UPLOADS_DIR = Path(__file__).parent / "static" / "uploads"
GENERATED_DIR = Path(__file__).parent / "static" / "generated"
LOGS_DIR = Path(__file__).parent / "experiment_logs"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 视频任务池
video_tasks = {}
video_executor = ThreadPoolExecutor(max_workers=2)

# Qwen API 配置 (请确保 key 正确)
API_KEY = "sk-fbdc82229399417892a94c001b5ea873" 
qwen = QwenChat()

# ================= 工具函数 =================

def dataurl_to_file(dataurl, filename=None):
    """将 base64 dataURL 转存为文件"""
    m = re.match(r"data:(image/\w+);base64,(.*)", dataurl, re.S)
    if not m:
        raise ValueError("不是合法的 data URL")
    mime, b64 = m.groups()
    ext = mime.split('/')[-1]
    
    if not filename:
        filename = f"{uuid.uuid4().hex}.{ext}"
    
    out_path = GENERATED_DIR / filename
    try:
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(b64))
    except Exception as e:
        print(f"Error writing file: {e}")
        raise
    return str(out_path)

def sanitize_filename_from_url(url):
    """生成安全的文件名"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if not ext or ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        ext = '.jpg'
    return f"{uuid.uuid4().hex}{ext}"

def download_to_generated(url, filename=None):
    """下载远程图片到 generated 目录"""
    try:
        if not filename:
            filename = sanitize_filename_from_url(url)
        out_path = GENERATED_DIR / filename
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return f"{BACKEND_BASE}/static/generated/{out_path.name}"
    except Exception as e:
        print("下载失败:", e)
        return None

def _resolve_local_path(url: str, base_dirs: Optional[List[Path]] = None) -> Optional[Path]:
    """
    【核心修复】强力解析本地路径
    无论传入的是 http://127.0.0.1:5000/static/generated/abc.jpg 
    还是 /static/uploads/abc.jpg
    都通过提取文件名来去硬盘里找文件。
    """
    if not url or not isinstance(url, str): return None
    if url.startswith("data:"): return None # 已经是base64了
    
    if base_dirs is None:
        base_dirs = [GENERATED_DIR, UPLOADS_DIR] # 优先找生成的图

    # 1. 提取文件名 (忽略路径前缀)
    try:
        parsed = urlparse(unquote(url))
        fname = os.path.basename(parsed.path) # 只取 abc.jpg
        if not fname or '.' not in fname:
            return None
    except:
        return None

    # 2. 在所有目录里查找这个文件名
    for base in base_dirs:
        candidate = base / fname
        if candidate.is_file():
            return candidate
            
    # 3. 如果没找到，尝试 fallback 扩展名 (jpg <-> png)
    stem, ext = os.path.splitext(fname)
    alternatives = ['.jpg', '.jpeg', '.png', '.webp']
    for alt_ext in alternatives:
        if alt_ext == ext: continue
        alt_name = stem + alt_ext
        for base in base_dirs:
            candidate = base / alt_name
            if candidate.is_file():
                return candidate

    return None

# ================= 核心业务路由 =================

@app.route('/upload-photo', methods=['POST'])
def upload_photo():
    try:
        if 'photo' not in request.files:
            return jsonify({"success": False, "message": "No photo provided"}), 400
        file = request.files['photo']
        if file.filename == '':
            return jsonify({"success": False, "message": "Empty filename"}), 400
        
        safe_name = secure_filename(file.filename) or f"{uuid.uuid4().hex}.jpg"
        name = f"{int(time.time())}_{safe_name}"
        filepath = UPLOADS_DIR / name
        file.save(filepath)
        url = f"/static/uploads/{name}"
        return jsonify({"success": True, "url": url})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/generate-prompts', methods=['POST'])
def generate_prompts():
    """
    Stage 3 & 4: 分句与 Prompt 生成
    """
    try:
        data = request.get_json()
        photos = data.get('photos', [])
        narratives = data.get('narrative', '')

        system_prompt_1 = """
        你是一个叙事视觉设计助手。任务：将文本转化为分镜式 Prompt 序列。

        【核心规则：视觉场景合并 (Visual Scene Merging)】
        1. **必须合并**：连续的句子如果描述的是同一个静止画面、同一个动作的持续状态、或者对同一场景的细节/心理补充，**必须合并为一个 Prompt**。
           - 例子："我坐在船头。" + "风吹过我的头发。" + "心情很舒畅。" -> 合并为一句。
        2. **切分条件**：只有当发生以下情况时才开启新 Prompt：
           - 明确的时间跳跃。
           - 地点的物理转换。
           - 视觉主体的根本改变。
        
        【Prompt 规范】
        - 包含：主体、动作、环境（含时代/地域特征）、光影氛围。
        - 约 20 字。
        - 必须具体可画，避免抽象形容词。
        
        【输出格式】
        JSON 数组：[{"sentence": "合并后的原句片段", "prompt": "画面描述"}]
        注意："sentence" 字段应当包含该画面对应的所有原文句子，以便后续追踪。
        """
        
        prompt_1 = f"文本内容：\n{narratives}\n请生成分镜 JSON。"

        response_1 = qwen.get_response(prompt=prompt_1, system_prompt=system_prompt_1, model="qwen-vl-max", enable_image_input=False)
        
        try:
            text_output = response_1 if isinstance(response_1, str) else response_1.get("output", {}).get("text", "")
            match = re.search(r'\[.*\]', text_output, re.DOTALL)
            qwen_sentences = json.loads(match.group(0)) if match else []
        except:
            print("Prompt生成JSON解析失败，降级处理")
            qwen_sentences = [{"sentence": narratives, "prompt": narratives}]

        # Photo-Sentence Matching
        sentence_pairs = []
        matched_indices = set()

        if photos:
            for photo_idx, photo in enumerate(photos):
                all_sents = "\n".join([f"{i}. {item['sentence'][:30]}..." for i, item in enumerate(qwen_sentences)])
                match_prompt = f"图片与以下哪个片段最匹配？返回索引JSON [{{'index': i, 'score': s}}]\n{all_sents}"
                
                try:
                    match_res = qwen.get_response(prompt=match_prompt, image_path_list=[photo], model="qwen-vl-max", enable_image_input=True)
                    match_json = re.search(r'\[.*\]', str(match_res), re.DOTALL)
                    scores = json.loads(match_json.group(0)) if match_json else []
                    
                    if scores:
                        best = max(scores, key=lambda x: x.get('score', 0))
                        best_idx = best.get('index', -1)
                        if best.get('score', 0) > 60 and best_idx not in matched_indices and 0 <= best_idx < len(qwen_sentences):
                            matched_indices.add(best_idx)
                            sentence_pairs.append({
                                "index": best_idx,
                                "photo": photo,
                                "sentence": qwen_sentences[best_idx]["sentence"],
                                "prompt": None 
                            })
                            continue
                except Exception as e:
                    print(f"Photo matching error: {e}")
                
                sentence_pairs.append({"index": photo_idx + 1000, "photo": photo, "sentence": None, "prompt": None})

        for idx, item in enumerate(qwen_sentences):
            if idx not in matched_indices:
                sentence_pairs.append({
                    "index": idx,
                    "photo": None,
                    "sentence": item["sentence"],
                    "prompt": item["prompt"]
                })
        
        sentence_pairs.sort(key=lambda x: x['index'])
        return jsonify({"sentence_pairs": sentence_pairs})

    except Exception as e:
        print("generate-prompts error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/generate-images', methods=['POST'])
def generate_images():
    try:
        payload = request.get_json()
        pairs = payload.get("sentence_pairs", [])
        if not pairs:
            return jsonify({"error": "no sentence_pairs"}), 400

        ig = MultiImage2Image()
        token = ig._encode_jwt_token()
        HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        def extract_base64(dataurl_or_b64: str) -> str:
            if dataurl_or_b64.startswith("data:image"):
                return dataurl_or_b64.split(",", 1)[1]
            return dataurl_or_b64

        def process_single_pair(item):
            idx = item.get("index", 0)
            prompt = item.get("prompt")
            if not prompt:
                return {"index": idx, "prompt": None, "generated_urls": [], "note": "no prompt"}

            photo_list = item.get("photo", [])
            if not photo_list:
                return {"index": idx, "error": "No reference photos provided"}
            
            proc_photos = photo_list[:4]
            if len(proc_photos) < 2:
                proc_photos = proc_photos * 2 

            try:
                subject_imgs = [{"subject_image": extract_base64(img)} for img in proc_photos]
                style_img_b64 = extract_base64(proc_photos[0])
                
                task_result = ig.run(
                    headers=HEADERS, prompt=prompt, subject_imgs=subject_imgs, style_img=style_img_b64,
                    model_name="kling-v2", n=1, aspect_ratio="3:4", max_wait=300, interval=5
                )
                
                generated_urls = []
                data = task_result.get("data", {})
                imgs = data.get("task_result", {}).get("images", []) or []
                for im in imgs:
                    remote_url = im.get("url")
                    if remote_url:
                        local_url = download_to_generated(remote_url)
                        if local_url: generated_urls.append(local_url)
                
                return {"index": idx, "prompt": prompt, "generated_urls": generated_urls}
            except Exception as e:
                print(f"Kling task failed for idx {idx}: {e}")
                return {"index": idx, "prompt": prompt, "generated_urls": [], "error": str(e)}

        results = [None] * len(pairs)
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {executor.submit(process_single_pair, item): i for i, item in enumerate(pairs)}
            for future in as_completed(future_to_index):
                try:
                    res = future.result()
                    results[future_to_index[future]] = res
                except Exception as e:
                    results[future_to_index[future]] = {"error": str(e)}

        return jsonify({"results": [r for r in results if r]})

    except Exception as e:
        print("generate-images error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    """Stage 2: 引导式提问 """
    try:
        data = request.get_json()
        photos = data.get('photos', [])
        narratives = data.get('narratives', '')

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
        prompt = f"用户提供的文字内容如下：\n{narratives}\n请结合上述内容和用户上传的照片生成一系列问题，严格遵守 system_prompt 中的 JSON 输出格式。"

        result = qwen.get_response(prompt=prompt, system_prompt=system_prompt, image_path_list=photos, model="qwen-vl-max", enable_image_input=True)
        
        try:
            match = re.search(r'\[.*\]', str(result), re.DOTALL)
            questions = json.loads(match.group(0)) if match else []
        except: questions = []

        return jsonify({"questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/integrate-text', methods=['POST'])
def integrate_text():
    """Stage 3: 整合 Narrative + QA"""
    try:
        data = request.get_json()
        narrative = data.get('narrative', '')
        qa_pairs = data.get('qa_pairs', [])
        qa_text = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in qa_pairs])

        system_prompt = """
        你是一个叙事作家。任务：将口述和问答整合成一段连贯、流畅、第一人称的叙事文本。
        必须融合 Narrative 和 Q&A 的所有信息，消除重复。只输出整合后的全文。
        """
        prompt = f"口述:\n{narrative}\n\n问答:\n{qa_text}\n\n请整合："
        
        result = qwen.get_response(prompt=prompt, system_prompt=system_prompt, model="qwen-vl-max", enable_image_input=False)
        return jsonify({"integrated_text": str(result).strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate-stage4-questions', methods=['POST'])
def generate_stage4_questions():
    """
    Stage 4: 假设-验证式提问
    【核心修复】：将前端传来的本地 URL 转换为 Base64 真正传给 Qwen。
    """
    try:
        data = request.get_json()
        # original_photos 是 base64 列表 (前端传来的)
        original_photos = data.get('original_photos', []) 
        # ai_photos_urls 是 URL 列表 (前端传来的, 可能是 localhost)
        ai_photos_urls = data.get('ai_photos_urls', [])   
        narrative = data.get('narrative', '')

        processed_ai_images = []
        
        print(f"[Stage 4] 收到 {len(ai_photos_urls)} 张 AI 图片 URL，准备转 Base64...")

        for url in ai_photos_urls:
            # 1. 尝试解析为本地文件路径
            local_path = _resolve_local_path(url)
            
            if local_path and local_path.exists():
                try:
                    # 2. 读取文件并转 Base64
                    with open(local_path, "rb") as f:
                        file_content = f.read()
                        b64_data = base64.b64encode(file_content).decode('utf-8')
                        
                        # 确定 MIME type
                        ext = local_path.suffix.lower()
                        if ext == '.png': mime = 'image/png'
                        elif ext == '.webp': mime = 'image/webp'
                        else: mime = 'image/jpeg'
                        
                        # 构造完整 Data URI
                        data_uri = f"data:{mime};base64,{b64_data}"
                        processed_ai_images.append(data_uri)
                except Exception as e:
                    print(f"⚠️ [Skip] 读取本地图片失败: {local_path.name}, 错误: {e}")
            else:
                # 如果找不到本地文件，跳过，防止发给 Qwen 报错
                print(f"⚠️ [Skip] 无法在本地找到图片: {url}，跳过此图。")

        # 合并所有图片（原图 Base64 + AI图 Base64）
        all_images = original_photos + processed_ai_images
        
        print(f"[Stage 4] 最终发送给 Qwen 的有效图片数量: {len(all_images)}")

        if not all_images:
             # 如果一张图都没有，虽然不理想，但至少返回空列表比报错好
            return jsonify({"questions": []})

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
        prompt = f"故事：\n{narrative}\n\n请仔细对比原始照片和 AI 生成的照片，针对 AI 生成图片中的新内容或氛围，提问 3-5 个具体问题，帮助用户回忆更多相关的故事或细节。严格遵守 system_prompt 中的 JSON 输出格式。"
        
        # 发送请求 (all_images 全是 base64，Qwen 能够接收)
        result = qwen.get_response(
            prompt=prompt, 
            system_prompt=system_prompt, 
            image_path_list=all_images, 
            model="qwen-vl-max", 
            enable_image_input=True
        )
        
        try:
            match = re.search(r'\[.*\]', str(result), re.DOTALL)
            questions = json.loads(match.group(0)) if match else []
        except: 
            questions = []
            
        return jsonify({"questions": questions})
        
    except Exception as e:
        print("❌ generate-stage4-questions Critical Error:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/update-text', methods=['POST'])
def update_text():
    """
    Stage 4: 文本更新 (In-place Rewriting)
    """
    try:
        data = request.get_json()
        current_narrative = data.get('current_narrative', '')
        new_qa_pairs = data.get('new_qa_pairs', [])
        if not new_qa_pairs: return jsonify({"updated_text": current_narrative})

        qa_text = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in new_qa_pairs])

        system_prompt = """
        你是一个专业的叙事编辑。
        你的任务是：将“新补充的问答细节”完美融合进“当前故事草稿”中，形成一篇连贯的完整故事。

        核心要求：
        1. **显式标记新增内容**：你必须把所有**基于Q&A新加入的细节、句子或对原句的重大修改**，用 `[NEW]` 和 `[/NEW]` 标签包裹起来。
           例如：那天天气很好，[NEW]阳光透过树叶洒在地上，像金色的碎片，[/NEW]我们心情都很不错。
        2. **深度融合**：将新信息插入到故事最合适的逻辑位置，不要只是堆砌在文末。
        3. **保持连贯**：确保未修改的部分和新加入的部分衔接自然。
        4. **只输出正文**：不要包含任何解释性语言。
        """
        
        prompt = f"现有文章：\n{current_narrative}\n\n补充信息：\n{qa_text}\n\n请输出修改后的完整文章："

        result = qwen.get_response(prompt=prompt, system_prompt=system_prompt, model="qwen-vl-max", enable_image_input=False)
        return jsonify({"updated_text": str(result).strip()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/save-experiment-log', methods=['POST'])
def save_experiment_log():
    try:
        data = request.get_json()
        log_data = data.get("log", {})
        user_id = str(log_data.get("userId", "anon"))
        session_id = str(log_data.get("sessionId", "unknown"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_dir = LOGS_DIR / user_id / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        clean_log = {k: v for k, v in log_data.items() if "Base64" not in k}
        json_path = session_dir / f"log_{ts}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(clean_log, f, ensure_ascii=False, indent=2)

        zip_path = session_dir / f"assets_{ts}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, url in enumerate(log_data.get("originalPhotoUrls", [])):
                p = _resolve_local_path(url)
                if p: zf.write(p, f"orig_{i}{p.suffix}")
            
            for i, url in enumerate(log_data.get("aiPhotoUrls", [])):
                p = _resolve_local_path(url)
                if p: zf.write(p, f"ai_{i}{p.suffix}")

        return jsonify({"success": True, "logJson": json_path.name})
    except Exception as e:
        print("Save log error:", e)
        return jsonify({"success": False, "message": str(e)}), 500

# ================= 视频生成相关 =================

@app.route('/refine-prompt', methods=['POST'])
def refine_prompt():
    """生成视频 Prompt - 支持单张照片的静态视频和照片对的过渡视频"""
    try:
        data = request.get_json()
        p_type = data.get("type", "transition")
        sentence = data.get("sentence", "")
        next_sent = data.get("next_sentence", "")
        photo_pair = data.get("photo_pair", [])  # 接收图片对或单张图片
        
        # 如果没有图片，使用原来的文本方式
        if not photo_pair:
            if p_type == "static":
                sys_p = "你是一名影视分镜师。为单张照片生成微动态视频指令。要求：描述照片中的静态场景，并添加一些微妙的动态元素，如光影变化、轻微的镜头移动等，让画面生动但不夸张。"
                content = f"画面：{sentence}"
            else:
                sys_p = "你是一名专业影视分镜师，精通视频首尾帧过渡效果设计。以图片 1 为视频首帧、图片 2 为尾帧，基于对两张图片内容的理解，生成一段视频制作指令。"
                content = f"起：{sentence}\n止：{next_sent}"
            result = qwen.get_response(prompt=content, system_prompt=sys_p, model="qwen-max", enable_image_input=False)
            return jsonify({"prompt": str(result).strip()})
        
        # 使用 analyze_images 分析图片
        try:
            # 1. 将图片下载到本地临时文件
            temp_images = []
            for i, photo_url in enumerate(photo_pair):
                local_path = _resolve_local_path(photo_url)
                if local_path and local_path.exists():
                    temp_images.append(str(local_path))
                else:
                    # 下载远程图片
                    fname = f"temp_{p_type}_{i}_{uuid.uuid4().hex}.jpg"
                    temp_path = GENERATED_DIR / fname
                    if photo_url.startswith('http'):
                        with requests.get(photo_url, stream=True) as r:
                            with open(temp_path, 'wb') as f:
                                for chunk in r.iter_content(8192):
                                    f.write(chunk)
                    temp_images.append(str(temp_path))
            
            if not temp_images:
                raise Exception("无法获取有效的图片")
                                    
            if p_type == "static":
                # 单张照片的静态转动态视频提示（强化自然可见动作，避免过度保守）
                custom_prompt = f"""
                你是一名专业的视频效果设计师。请深度理解这张照片的核心内容与人物状态：
                
                照片描述：{sentence}
                
                请为这张照片设计一段静态转动态的视频效果指令，要求：
                1. 基于照片原有人物形象与场景，为人物设计**符合人体规律、幅度适中可见的自然动作**，如缓慢转头环视四周、抬手轻理衣角/发丝、身体轻微侧倾调整姿态、手指轻触身旁道具、缓慢眨眼配合轻微头部点动等，动作需连贯且有细节，避免过度保守导致画面近乎静止
                2. 搭配微妙的辅助动态效果，如柔和光影渐变、轻微镜头推进/拉远，动态节奏需与人物动作完全匹配，增强画面层次感
                3. 整体保持画面稳定性和宁静感，动作不夸张、不破坏照片原有氛围与风格
                4. 指令需详细具体，紧扣照片元素，可直接作为AI视频生成工具的输入
                5. 内容详实且逻辑清晰，总字数控制在400字以内
                
                请直接输出完整的视频效果描述。
                """
            else:
                # 照片对的过渡视频提示（强化核心约束+禁止新增主体）
                custom_prompt = f"""
                你是一名专业的视频过渡效果设计师，精通首尾帧过渡逻辑。请深度理解以下两张连续照片的内容，为其设计自然流畅的视频过渡效果指令：
                
                第一张照片描述：{sentence}
                第二张照片描述：{next_sent}
                
                核心要求：
                1. 过渡过程**不得新增任何画面主体**，仅基于两张照片原有元素进行演变融合
                2. 背景过渡采用旋转、镜头靠近或缩小的动态方式，严禁使用淡化类效果，杜绝背景瞬时切换
                3. 人物动作需符合人体规律，禁止过分迅速转头、夸张姿态等不符合现实的动作，动作从首帧状态缓慢渐进过渡至尾帧，幅度柔和不突兀
                4. 详细描述过渡的视觉变化过程，包含运动方向、镜头移动轨迹、场景融合逻辑，确保人物动作与背景动态节奏完全匹配
                5. 指令紧扣两张照片元素，可直接作为AI视频生成工具的输入，内容详实、逻辑清晰
                6. 总字数控制在400字以内
                
                请直接输出完整的过渡效果描述。
                """
            
            result = analyze_images(temp_images, custom_prompt)
            
            # 3. 清理临时文件
            for img_path in temp_images:
                if img_path.startswith(str(GENERATED_DIR)) and 'temp_' in img_path:
                    try:
                        os.unlink(img_path)
                    except:
                        pass
            
            return jsonify({"prompt": str(result).strip()})
            
        except Exception as img_error:
            print(f"analyze_images 失败: {img_error}")
            # 降级使用原来的文本方式
            if p_type == "static":
                sys_p = "你是一名影视分镜师。为单张照片生成微动态视频指令。"
                content = f"画面：{sentence}"
            else:
                sys_p = "你是一名影视分镜师。为两张照片生成平滑过渡视频指令。"
                content = f"起：{sentence}\n止：{next_sent}"
            result = qwen.get_response(prompt=content, system_prompt=sys_p, model="qwen-max", enable_image_input=False)
            return jsonify({"prompt": str(result).strip()})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate-video', methods=['POST'])
def generate_video():
    try:
        data = request.get_json()
        photo_urls = data.get("photos", [])
        prompts = data.get("prompts", [])
        
        if len(photo_urls) < 2: return jsonify({"error": "Need > 2 photos"}), 400

        task_id = str(uuid.uuid4())
        video_tasks[task_id] = {"status": "pending", "start_time": time.time()}
        
        video_executor.submit(_run_video_generation_task, task_id, photo_urls, prompts)
        
        return jsonify({"task_id": task_id, "status": "submitted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _run_video_generation_task(task_id, photo_urls, prompts):
    temp_dir = None
    try:
        video_tasks[task_id]["status"] = "downloading"
        temp_dir = Path(tempfile.mkdtemp())
        local_paths = []

        # 下载图片
        for url in photo_urls:
            local_path = _resolve_local_path(url)
            if not local_path:
                fname = sanitize_filename_from_url(url)
                local_path = temp_dir / fname
                with requests.get(url, stream=True) as r:
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(8192): f.write(chunk)
            local_paths.append(str(local_path))

        video_tasks[task_id]["status"] = "generating"
        out_name = f"final_{uuid.uuid4().hex}.mp4"
        out_path = GENERATED_DIR / out_name

        # 调用命令行生成
        cmd = ["python", "generate.py", "--photos", *local_paths, "--prompts", *[str(p) for p in prompts]]
        subprocess.run(cmd, check=True, cwd=os.path.dirname(__file__))

        video_tasks[task_id].update({"status": "success", "videoUrl": f"{BACKEND_BASE}/static/generated/{out_name}"})

    except Exception as e:
        print(f"Video task {task_id} failed: {e}")
        video_tasks[task_id].update({"status": "failed", "error": str(e)})
    finally:
        if temp_dir and temp_dir.exists(): shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/video-status/<task_id>', methods=['GET'])
def video_status(task_id):
    task = video_tasks.get(task_id)
    if not task: return jsonify({"error": "not found"}), 404
    return jsonify(task)

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)