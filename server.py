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

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 确保 static/generated 目录存在（Flask 默认会把 /static 映射到 ./static）
GENERATED_DIR = Path(__file__).parent / "static" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# 定义后端对外访问的 base 地址（用于返回绝对 URL）
BACKEND_BASE = "http://127.0.0.1:5000"

# # helper: 把 data:image/...;base64,... 写成文件，返回文件路径
# def dataurl_to_file(dataurl, filename=None):
#     """
#     dataurl example: "data:image/jpeg;base64,/9j/4AAQ.."
#     返回写好的文件路径（字符串）
#     """
#     m = re.match(r"data:(image/\w+);base64,(.*)", dataurl, re.S)
#     if not m:
#         raise ValueError("不是合法的 data URL")
#     mime, b64 = m.groups()
#     ext = mime.split('/')[-1]
#     if not filename:
#         filename = f"{uuid.uuid4().hex}.{ext}"
#     out_path = GENERATED_DIR / filename
#     with open(out_path, "wb") as f:
#         f.write(base64.b64decode(b64))
#     return str(out_path)
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
# @app.route('/generate-images', methods=['POST'])
# def generate_images():
#     """
#     接收前端传来的 sentence_pairs（同你前端控制台输出结构），
#     对 prompt != null 的项逐条调用 kling ImageGenerator，等待结果，
#     把返回的图片下载到 ./static/generated 并返回本地 URL 列表。
#     请求体示例:
#     {
#       "sentence_pairs": [{ "photo": "...dataurl或null...", "sentence": "...", "prompt": "..." }, ...]
#     }
#     """
#     try:
#         payload = request.get_json()
#         pairs = payload.get("sentence_pairs", [])
#         # photos = payload.get("photos", [])
#         if not pairs:
#             return jsonify({"error": "no sentence_pairs"}), 400

#         # 初始化 ImageGenerator
#         # ig = ImageGenerator()  # 使用 kling.py 中的类；确保 ACCESS/SECRET 在 kling.py 已设置
#         ig = MultiImage2Image()

#         # 构造 Authorization header（kling 的示例中用 jwt）
#         token = ig._encode_jwt_token()  # 直接利用类方法生成 token
#         AUTHORIZATION = f"Bearer {token}"
#         HEADERS = {"Content-Type": "application/json", "Authorization": AUTHORIZATION}

#         results = []  # 收集每个 prompt 的返回信息

#         for idx, item in enumerate(pairs):
#             prompt = item.get("prompt")
#             # ✅ [修改] 确保使用 item 中传递的 index（如果存在）
#             item_index = item.get("index", idx) 
            
#             if not prompt:
#                 # 跳过没有 prompt 的项（front-end 不需要生成）
#                 results.append({"index": item_index, "prompt": None, "generated_urls": [], "note": "no prompt"})
#                 continue

#             # 如果该项自带 photo（data url），写成临时文件并传给 kling
#             local_input_path = None
#             photo = item.get("photo")

#             if isinstance(photo, list) and photo:
#                 subject_imgs = photo if photo else []
#                 print(f"Item {item_index} has photo list, taking first element as style_photo.")
#                 photo = photo[0] 

#             print(f"Type of photo for item {item_index}: {type(photo)}")  # 打印 photo 的类型
#             print(f"photo for item {item_index}: {photo[:100]}")  # 打印每个 item 的 photo 值

#             if photo and isinstance(photo, str) and photo.startswith("data:"):
#                 try:
#                     print('{item_index}写入 dataurl 图片...')
#                     local_input_path = dataurl_to_file(photo, filename=f"input_{uuid.uuid4().hex}.jpg")
#                     print("{item_index}写入临时输入图片:", local_input_path)
#                 except Exception as e:
#                     print("写入 dataurl 失败:", e)
#                     local_input_path = None

#             # 调用 ImageGenerator.run（同步轮询）
#             try:
#                 task_result = ig.run(
#                     headers=HEADERS,
#                     prompt=prompt,
#                     subject_imgs = subject_imgs,
#                     style_img=local_input_path if local_input_path else "",
#                     model_name="kling-v2",
#                     n=1,
#                     aspect_ratio="3:4",
#                     max_wait=300,
#                     interval=5
#                 )
#             except Exception as e:
#                 print("调用 kling 失败:", e)
#                 results.append({"index": item_index, "prompt": prompt, "generated_urls": [], "error": str(e)})
#                 continue

#             # 从 task_result 中提取图片 url（格式依赖 kling 返回的结构）
#             generated_urls = []
#             try:
#                 data = task_result.get("data", {})
#                 # 适配你 kling.py get_task_result 中返回的结构
#                 imgs = data.get("task_result", {}).get("images", []) or []
#                 for im in imgs:
#                     # im 里通常包含 'url' 字段（远程可访问）
#                     remote_url = im.get("url")
#                     if not remote_url:
#                         # 如果返回的是 base64 字符串字段（示例），可按需写入文件：
#                         b64 = im.get("b64") or im.get("base64")
#                         if b64:
#                             # 写成文件并返回本地 url
#                             try:
#                                 fn = f"{uuid.uuid4().hex}.jpg"
#                                 out_path = GENERATED_DIR / fn
#                                 with open(out_path, "wb") as f:
#                                     f.write(base64.b64decode(b64))
#                                 generated_urls.append(f"{BACKEND_BASE}/static/generated/{out_path.name}")
#                             except Exception as e:
#                                 print("写入 base64 图片失败:", e)
#                         continue

#                     # 先尝试下载到本地静态目录（使用 safe filename）
#                     local_url = download_to_generated(remote_url)
#                     if local_url:
#                         generated_urls.append(local_url)
#                     else:
#                         # 如果下载失败，仍然把远程 URL 返回给前端（前端可直接使用远端URL）
#                         generated_urls.append(remote_url)

#             except Exception as e:
#                 print("解析生成结果失败:", e)

#             results.append({"index": item_index, "prompt": prompt, "generated_urls": generated_urls})
#         # 返回一个数组，前端按 index 对应处理
#         return jsonify({"results": results})

#     except Exception as e:
#         print("generate-images 异常:", e)
#         return jsonify({"error": str(e)}), 500
@app.route('/generate-images', methods=['POST'])
def generate_images():
    """
    接收前端传来的 sentence_pairs，对 prompt != null 的项调用 MultiImage2Image 生成图片。
    每个 item 的 photo 字段为 base64 字符串数组（参考图），取前4张作为 subject_imgs，
    第1张同时作为 style_img（传入 style_img 参数）。
    """
    try:
        payload = request.get_json()
        pairs = payload.get("sentence_pairs", [])
        if not pairs:
            return jsonify({"error": "no sentence_pairs"}), 400

        ig = MultiImage2Image()

        token = ig._encode_jwt_token()
        AUTHORIZATION = f"Bearer {token}"
        HEADERS = {"Content-Type": "application/json", "Authorization": AUTHORIZATION}

        results = []

        for idx, item in enumerate(pairs):
            prompt = item.get("prompt")
            item_index = item.get("index", idx)

            if not prompt:
                results.append({"index": item_index, "prompt": None, "generated_urls": [], "note": "no prompt"})
                continue

            # ✅【关键修改】处理 photo 数组：前端传的是 base64 字符串列表
            photo_list = item.get("photo", [])  # List[str], each is base64 (data URL or pure b64)
            if not isinstance(photo_list, list):
                photo_list = []

            # 若为空，无法生成（可灵要求至少2张主体图）
            if len(photo_list) < 2:
                results.append({
                    "index": item_index,
                    "prompt": prompt,
                    "generated_urls": [],
                    "error": "subject_imgs must contain at least 2 images"
                })
                continue

            # 取前4张
            subject_photo_list = photo_list[:4]  # 最多4张

            # 转为可灵要求的 subject_image_list 格式：[{"subject_image": b64_str}, ...]
            # 注意：可灵 API 支持纯 base64 字符串（无需 "data:image/..." 前缀），但若含 dataurl 需处理
            def extract_base64(dataurl_or_b64: str) -> str:
                if dataurl_or_b64.startswith("data:image"):
                    # 截取 base64 部分（跳过 MIME 头）
                    try:
                        b64_part = dataurl_or_b64.split(",", 1)[1]
                        return b64_part
                    except IndexError:
                        raise ValueError("Invalid data URL format")
                else:
                    # 假设已是纯 base64（可灵接受）
                    return dataurl_or_b64

            try:
                # 构建 subject_imgs：list of dict {"subject_image": b64_str}
                subject_imgs = [
                    {"subject_image": extract_base64(img)} for img in subject_photo_list
                ]

                # style_img 使用第一张图的 base64 字符串（注意：是字符串，不是 dict）
                style_img_b64 = extract_base64(subject_photo_list[0])
                # 注意：MultiImage2Image.run() 中 style_img 传入的是字符串（支持 base64 或 URL）

            except Exception as e:
                results.append({
                    "index": item_index,
                    "prompt": prompt,
                    "generated_urls": [],
                    "error": f"photo preprocessing failed: {str(e)}"
                })
                continue

            # ✅ 调用 MultiImage2Image.run()
            try:
                task_result = ig.run(
                    headers=HEADERS,
                    prompt=prompt,
                    subject_imgs=subject_imgs,         # ✔️ 已为正确格式
                    style_img=style_img_b64,           # ✔️ 第一张图的 base64 字符串
                    model_name="kling-v2",
                    n=1,
                    aspect_ratio="3:4",
                    max_wait=300,
                    interval=5
                )
            except Exception as e:
                results.append({
                    "index": item_index,
                    "prompt": prompt,
                    "generated_urls": [],
                    "error": f"kling run failed: {str(e)}"
                })
                continue

            # ✅ 提取结果
            generated_urls = []
            try:
                data = task_result.get("data", {})
                imgs = data.get("task_result", {}).get("images", []) or []
                for im in imgs:
                    remote_url = im.get("url")
                    if remote_url:
                        local_url = download_to_generated(remote_url)
                        generated_urls.append(local_url or remote_url)
                    else:
                        b64 = im.get("b64") or im.get("base64")
                        if b64:
                            try:
                                fn = f"{uuid.uuid4().hex}.jpg"
                                out_path = GENERATED_DIR / fn
                                out_path.write_bytes(base64.b64decode(b64))
                                generated_urls.append(f"{BACKEND_BASE}/static/generated/{out_path.name}")
                            except Exception as ex:
                                print(f"Base64 save failed for item {item_index}:", ex)
            except Exception as e:
                print(f"Parse result failed for item {item_index}:", e)

            results.append({
                "index": item_index,
                "prompt": prompt,
                "generated_urls": generated_urls
            })

        return jsonify({"results": results})

    except Exception as e:
        print("generate-images exception:", e)
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

UPLOADS_DIR = Path(__file__).parent / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

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

# 图像存储根目录（与 upload / generate-images 一致）
UPLOADS_DIR = Path(__file__).parent / "static" / "uploads"
GENERATED_DIR = Path(__file__).parent / "static" / "generated"


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


def _resolve_local_path(url: str, base_dir: Path) -> Path | None:
    """
    将前端传来的 URL（绝对/相对/本地）解析为服务器本地 Path
    支持：
      - http://127.0.0.1:5000/static/uploads/xxx.jpg
      - /static/uploads/xxx.jpg
      - blob:http://... (不可解析 → None)
    """
    if not url or not isinstance(url, str):
        return None

    # 忽略 blob URL（前端应在 save 前转为本地路径）
    if url.startswith("blob:"):
        return None

    # 解析路径部分
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)

        # 移除 /static/ 前缀（如果存在）
        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
        else:
            rel_path = path.lstrip("/")

        # 尝试拼接 base_dir (uploads 或 generated)
        candidate = base_dir / rel_path
        if candidate.exists() and candidate.is_file():
            return candidate

        # 备用：直接按文件名在 base_dir 下查找（防路径偏移）
        filename = os.path.basename(rel_path)
        if filename:
            fallback = base_dir / filename
            if fallback.exists() and fallback.is_file():
                return fallback

        return None
    except Exception as e:
        print(f"⚠️ _resolve_local_path error for {url}: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)