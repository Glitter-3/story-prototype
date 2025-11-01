import os
import re
import json
import uuid
import base64
import requests
from pathlib import Path
from kling import ImageGenerator
from urllib.parse import urlparse, unquote
import string
from flask import Flask, request, jsonify
from qwen import QwenChat
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 确保 static/generated 目录存在（Flask 默认会把 /static 映射到 ./static）
GENERATED_DIR = Path(__file__).parent / "static" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# 定义后端对外访问的 base 地址（用于返回绝对 URL）
BACKEND_BASE = "http://127.0.0.1:5000"

# helper: 把 data:image/...;base64,... 写成文件，返回文件路径
def dataurl_to_file(dataurl, filename=None):
    """
    dataurl example: "data:image/jpeg;base64,/9j/4AAQ.."
    返回写好的文件路径（字符串）
    """
    m = re.match(r"data:(image/\w+);base64,(.*)", dataurl, re.S)
    if not m:
        raise ValueError("不是合法的 data URL")
    mime, b64 = m.groups()
    ext = mime.split('/')[-1]
    if not filename:
        filename = f"{uuid.uuid4().hex}.{ext}"
    out_path = GENERATED_DIR / filename
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))
    return str(out_path)

# helper: 下载远程url到 static/generated 并返回本地相对路径（供前端访问）
def sanitize_filename_from_url(url):
    """
    从 URL 解析出一个适合作为本地文件名的 basename（移除 query，保留扩展）
    """
    parsed = urlparse(url)
    # 取 path 的最后一段
    base = os.path.basename(parsed.path)
    base = unquote(base)  # 解码 %20 等
    if not base:
        base = uuid.uuid4().hex
    # 仅保留允许字符，防止 windows 无效字符
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    cleaned = ''.join(c for c in base if c in valid_chars)
    if not os.path.splitext(cleaned)[1]:
        # 如果没扩展名，默认用 .jpg
        cleaned = cleaned + ".jpg"
    # 防止名字过长
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    return cleaned

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

# 新增路由：/generate-images
@app.route('/generate-images', methods=['POST'])
def generate_images():
    """
    接收前端传来的 sentence_pairs（同你前端控制台输出结构），
    对 prompt != null 的项逐条调用 kling ImageGenerator，等待结果，
    把返回的图片下载到 ./static/generated 并返回本地 URL 列表。
    请求体示例:
    {
      "sentence_pairs": [{ "photo": "...dataurl或null...", "sentence": "...", "prompt": "..." }, ...]
    }
    """
    try:
        payload = request.get_json()
        pairs = payload.get("sentence_pairs", [])
        if not pairs:
            return jsonify({"error": "no sentence_pairs"}), 400

        # 初始化 ImageGenerator
        ig = ImageGenerator()  # 使用 kling.py 中的类；请确保 ACCESS/SECRET 在 kling.py 已设置

        # 构造 Authorization header（kling 的示例中用 jwt）
        token = ig._encode_jwt_token()  # 直接利用类方法生成 token
        AUTHORIZATION = f"Bearer {token}"
        HEADERS = {"Content-Type": "application/json", "Authorization": AUTHORIZATION}

        results = []  # 收集每个 prompt 的返回信息

        for idx, item in enumerate(pairs):
            prompt = item.get("prompt")
            # ✅ [修改] 确保使用 item 中传递的 index（如果存在）
            item_index = item.get("index", idx) 
            
            if not prompt:
                # 跳过没有 prompt 的项（front-end 不需要生成）
                results.append({"index": item_index, "prompt": None, "generated_urls": [], "note": "no prompt"})
                continue

            # 如果该项自带 photo（data url），写成临时文件并传给 kling
            local_input_path = None
            photo = item.get("photo")
            if photo and isinstance(photo, str) and photo.startswith("data:"):
                try:
                    local_input_path = dataurl_to_file(photo, filename=f"input_{uuid.uuid4().hex}.jpg")
                except Exception as e:
                    print("写入 dataurl 失败:", e)
                    local_input_path = None

            # 调用 ImageGenerator.run（同步轮询）
            try:
                task_result = ig.run(
                    headers=HEADERS,
                    prompt=prompt,
                    image_path=local_input_path if local_input_path else "",
                    model_name="kling-v2",
                    n=1,
                    aspect_ratio="3:4",
                    max_wait=300,
                    interval=5
                )
            except Exception as e:
                print("调用 kling 失败:", e)
                results.append({"index": item_index, "prompt": prompt, "generated_urls": [], "error": str(e)})
                continue

            # 从 task_result 中提取图片 url（格式依赖 kling 返回的结构）
            generated_urls = []
            try:
                data = task_result.get("data", {})
                # 适配你 kling.py get_task_result 中返回的结构
                imgs = data.get("task_result", {}).get("images", []) or []
                for im in imgs:
                    # im 里通常包含 'url' 字段（远程可访问）
                    remote_url = im.get("url")
                    if not remote_url:
                        # 如果返回的是 base64 字符串字段（示例），可按需写入文件：
                        b64 = im.get("b64") or im.get("base64")
                        if b64:
                            # 写成文件并返回本地 url
                            try:
                                fn = f"{uuid.uuid4().hex}.jpg"
                                out_path = GENERATED_DIR / fn
                                with open(out_path, "wb") as f:
                                    f.write(base64.b64decode(b64))
                                generated_urls.append(f"{BACKEND_BASE}/static/generated/{out_path.name}")
                            except Exception as e:
                                print("写入 base64 图片失败:", e)
                        continue

                    # 先尝试下载到本地静态目录（使用 safe filename）
                    local_url = download_to_generated(remote_url)
                    if local_url:
                        generated_urls.append(local_url)
                    else:
                        # 如果下载失败，仍然把远程 URL 返回给前端（前端可直接使用远端URL）
                        generated_urls.append(remote_url)

            except Exception as e:
                print("解析生成结果失败:", e)

            results.append({"index": item_index, "prompt": prompt, "generated_urls": generated_urls})
        # 返回一个数组，前端按 index 对应处理
        return jsonify({"results": results})

    except Exception as e:
        print("generate-images 异常:", e)
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
        你是一个叙事视觉设计助手。
        请把用户给出的叙述文本合理分句，每句代表一个独立的视觉场景。
        对每一句生成一个适合文生图的中文prompt（约20字，描述画面内容）。
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






if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)