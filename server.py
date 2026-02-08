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
import tempfile
import shutil
import cv2
import numpy as np
from sklearn.cluster import DBSCAN


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


#人脸自动识别
@app.route('/analyze-characters', methods=['POST'])
def analyze_characters():
    try:
        data = request.get_json()
        photos = data.get('photos', [])
        
        characters = []
        global_face_idx = 0
        
        # 使用更准确的人脸检测器配置
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        for p_idx, photo_info in enumerate(photos):
            if isinstance(photo_info, dict):
                base64_data = photo_info.get('base64', '')
            else:
                base64_data = str(photo_info)
            
            print(f"正在处理图片 {p_idx}, base64 数据长度: {len(base64_data)}")
                
            try:
                # 【关键修复】正确解析 base64 数据
                if base64_data.startswith('data:image'):
                    base64_data = base64_data.split(',', 1)[1]
                elif base64_data.startswith('image'):
                    base64_data = base64_data.split(',', 1)[1]
                
                if not base64_data or len(base64_data) < 100:
                    print(f"图片 {p_idx} 的 base64 数据过短或为空")
                    continue
                
                # 解码图片
                img_data = base64.b64decode(base64_data)
                np_arr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if img is None:
                    print(f"无法解码图片索引 {p_idx}，可能是 base64 格式错误")
                    continue
                
                print(f"成功解码图片 {p_idx}, 尺寸: {img.shape}")
                
                # 调整图像大小
                height, width = img.shape[:2]
                if max(height, width) > 1000:
                    scale = 1000.0 / max(height, width)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    img = cv2.resize(img, (new_width, new_height))
                    print(f"调整图片 {p_idx} 尺寸为: {new_width}x{new_height}")
                
                # 转换为灰度图
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # 使用更严格的参数检测人脸
                faces = face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1,
                    minNeighbors=8,
                    minSize=(50, 50),
                    maxSize=(300, 300),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                
                print(f"在图片 {p_idx} 中检测到 {len(faces)} 个候选区域")
                
                valid_faces = []
                for (x, y, w, h) in faces:
                    
                    # 【修改点1】扩展更大的边界框，包含更多衣着信息
                    # 水平方向扩展 30%，垂直方向扩展更多（上方扩展 20%，下方扩展 80%）
                    x_expand = int(w * 0.3)  # 左右各扩展30%
                    y_expand_top = int(h * 0.2)   # 上方扩展20%
                    y_expand_bottom = int(h * 0.8) # 下方扩展80%，包含更多身体和衣着
                    
                    x1 = max(0, x - x_expand)
                    y1 = max(0, y - y_expand_top)
                    x2 = min(img.shape[1], x + w + x_expand)
                    y2 = min(img.shape[0], y + h + y_expand_bottom)
                    
                    # 【修改点2】确保宽高比合理，避免过于细长
                    current_width = x2 - x1
                    current_height = y2 - y1
                    
                    # 如果高度不足宽度的1.2倍，增加高度
                    if current_height < current_width * 1.2:
                        needed_height = int(current_width * 1.2)
                        additional_height = needed_height - current_height
                        y2 = min(img.shape[0], y2 + additional_height)
                    
                    face_img = img[y1:y2, x1:x2]
                    
                    # 【修改点3】如果裁剪后的图像太小，跳过
                    if face_img.size == 0 or face_img.shape[0] < 50 or face_img.shape[1] < 50:
                        continue
                        
                    valid_faces.append((x1, y1, x2-x1, y2-y1, face_img))

                
                print(f"经过验证后，有效人脸数量: {len(valid_faces)}")
                
                # 处理有效人脸
                for (x1, y1, w, h, face_img) in valid_faces:
                    success, buffer = cv2.imencode('.jpg', face_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    if success:
                        face_b64 = base64.b64encode(buffer).decode('utf-8')
                        
                        # 【关键修复】将 numpy 类型转换为 Python 原生类型
                        characters.append({
                            "id": global_face_idx,
                            "name": f"人物 {global_face_idx + 1}",
                            "relationType": "", 
                            "customRelation": "",
                            "isMain": False,
                            "avatar": f"data:image/jpeg;base64,{face_b64}",
                            "photoIndex": p_idx,
                            "photoUrl": photo_info.get('url', '') if isinstance(photo_info, dict) else '',
                            "aiPhotoUrls": [],
                            "confidence": 1.0,
                            # 【修改点4】添加裁剪区域信息，并确保使用 Python 原生类型
                            "cropInfo": {
                                "x": int(x1),  # 转换为 int
                                "y": int(y1),  # 转换为 int
                                "width": int(w),  # 转换为 int
                                "height": int(h),  # 转换为 int
                                "originalWidth": int(img.shape[1]),  # 转换为 int
                                "originalHeight": int(img.shape[0])  # 转换为 int
                            }
                        })
                        global_face_idx += 1
                        print(f"  成功提取人物区域 {global_face_idx}, 尺寸: {w}x{h}")
                        
            except Exception as e:
                print(f"处理照片 {p_idx} 出错: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"总共检测到 {len(characters)} 个有效人物区域")
        
        if len(characters) == 0:
            print("⚠️ 未检测到有效人物区域")
            return jsonify({"characters": []})

        return jsonify({"characters": characters})

    except Exception as e:
        print(f"analyze-characters 总体出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500




@app.route('/group-photos-by-time', methods=['POST'])
def group_photos_by_time():
    """
    Stage 1: 对用户上传的照片按时间进行分组（可基于Qwen-VL视觉分析或用户口述）
    """
    try:
        data = request.get_json()
        photos = data.get('photos', [])  # base64 列表
        narrative = data.get('narrative', '')  # 用户口述（可选）

        if not photos:
            return jsonify({"error": "No photos provided"}), 400

        # 构造Qwen提示词，要求对照片按时间顺序分组
        system_prompt = """
        你是一位视觉记忆分析师。现在用户提供若干张照片和可能的文字口述。
        你的任务是对这些照片按**时间顺序**划分为若干组（每组代表一个阶段或事件），
        并为每组起一个简短的时间阶段名称（如“童年时期”、“大学时光”、“疫情居家”等）。

        要求：
        1. 每张照片只能属于一个组。
        2. 按时间从前到后排序。
        3. 输出严格为 JSON 格式，结构如下：
        {
          "groups": [
            {
              "name": "阶段名称",
              "photo_indices": [0, 1, 2]  // 照片在输入列表中的索引
            },
            ...
          ]
        }
        4. 如果无法判断时间顺序，请按上传顺序分组，每张照片一组。
        """

        prompt = f"用户口述（如有）：{narrative}\n\n请分析以下照片的时间顺序并分组。"

        # 调用 Qwen-VL（启用图片输入）
        response = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=photos,
            model="qwen-vl-max",
            enable_image_input=True
        )

        # 提取 JSON
        try:
            text_output = response if isinstance(response, str) else response.get("output", {}).get("text", "")
            match = re.search(r'\{.*\}', text_output, re.DOTALL)
            result = json.loads(match.group(0)) if match else {"groups": []}
        except Exception as e:
            print("JSON解析失败，使用兜底方案：每张图一组")
            result = {
                "groups": [
                    {"name": f"阶段 {i+1}", "photo_indices": [i]}
                    for i in range(len(photos))
                ]
            }

        return jsonify(result)

    except Exception as e:
        print("group-photos-by-time error:", e)
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈
        return jsonify({"error": str(e)}), 500
    

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

# @app.route('/generate-questions', methods=['POST'])
# def generate_questions():
#     """Stage 2: 引导式提问 """
#     try:
#         data = request.get_json()
#         photos = data.get('photos', [])
#         narratives = data.get('narratives', '')

#         system_prompt = """
#             你是一名专业的记忆研究助理。
#             你的任务是：根据用户提供的照片和文字描述，生成帮助用户回忆的开放性问题。
#             要求：
#             1. 严格输出 JSON 数组。
#             2. 数组中每个元素是对象，必须包含字段：
#             - text: 问题内容
#             - answer: 空字符串
#             - answered: false
#             - showInput: false
#             3. 不要生成回答，只输出问题。
#             4. 语言使用中文。
#             5. 提问的维度可以包括时间、地点、人物、场景、情感等。
#             示例：
#             [
#             {"text": "请描述这张照片中的人物是谁？", "answer": "", "answered": false, "showInput": false},
#             {"text": "照片中的场景对你意味着什么？", "answer": "", "answered": false, "showInput": false}
#             ]
#             """
#         prompt = f"用户提供的文字内容如下：\n{narratives}\n请结合上述内容和用户上传的照片生成一系列问题，严格遵守 system_prompt 中的 JSON 输出格式。"

#         result = qwen.get_response(prompt=prompt, system_prompt=system_prompt, image_path_list=photos, model="qwen-vl-max", enable_image_input=True)
        
#         try:
#             match = re.search(r'\[.*\]', str(result), re.DOTALL)
#             questions = json.loads(match.group(0)) if match else []
#         except: questions = []

#         return jsonify({"questions": questions})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    """
    Stage 2: 基于照片分组的引导式提问生成
    """
    try:
        data = request.get_json()

        photo_groups = data.get('photoGroups', [])
        narratives = data.get('narratives', '')

        # -------- 1. 展平所有照片，供 Qwen 使用 --------
        all_photos = []
        for g in photo_groups:
            all_photos.extend(g.get("photos", []))

        # -------- 2. 给模型看的分组结构（只含语义） --------
        groups_for_prompt = []
        for idx, g in enumerate(photo_groups):
            groups_for_prompt.append({
                "group_id": idx,
                "title": g.get("name", f"分组{idx+1}"),
                "photo_count": len(g.get("photos", []))
            })

        print("\n📤 ===== INPUT TO QWEN =====")
        print("🧩 Groups:")
        print(json.dumps(groups_for_prompt, ensure_ascii=False, indent=2))
        print("📝 Narratives:")
        print(narratives)
        print("🖼️ Total photos:", len(all_photos))
        print("================================\n")

        # -------- 3. System Prompt --------
        system_prompt = """
你是一名专业的记忆研究与人生叙事引导助理。

你的任务是：
基于【用户的照片分组结构】、【照片内容】以及【已有文字口述】，生成有助于用户回忆与讲述人生故事的引导式问题。

请遵循以下原则：

一、问题类型

1. 组内提问（type = "intra"）
- 针对单个照片分组（人生阶段 / 章节）内部
- 提问维度可参考（但不要求全部覆盖）：
  人物（Who）、时间（When）、地点（Where）、事件（What）、情感与感受
- 并非每个分组都必须提问
- 每个分组只提出你认为“最关键、最有价值”的 2–4 个问题即可

2. 组间提问（type = "inter"）
- 针对相邻或逻辑相关的两个分组
- 不重复具体照片细节
- 重点关注：
  人生阶段之间的动因、转折、选择、影响或内在变化

二、重要约束
- 按照时间阶段提问。即第一组组内问题优先，接着是第一组与第二组的组间问题，然后是第二组组内问题，依此类推。
- 4W + 情感只是参考维度，而不是检查表
- 你需要根据具体照片内容与分组主题自行判断：
  是否需要提问、问什么、问多少
- 总共提出 8-10 个问题（组内 + 组间）
- 提问的答案汇总起来得到的信息需要能完整连缀整个故事，明确回答人物（Who）、时间（When）、地点（Where）、事件（What）、情感与感受。

三、输出格式（必须严格遵守）
- 只输出一个 JSON 数组
- 每个元素是一个对象，字段如下：

{
  "type": "intra" | "inter",

  "group_id": number | null,
  "left_group_id": number | null,
  "right_group_id": number | null,

  "text": string,
  "answer": "",
  "answered": false,
  "showInput": false
}

字段约束说明（必须遵守）：
- 如果 type = "intra"：
  - group_id 必须为对应分组的 group_id
  - left_group_id 与 right_group_id 必须为 null

- 如果 type = "inter"：
  - group_id 必须为 null
  - left_group_id 与 right_group_id 必须分别填写两个相关分组的 group_id

- 不输出任何解释性文字
- 不生成回答
- 使用中文
"""
        prompt = f"""
以下是用户整理后的照片分组结构：

{json.dumps(groups_for_prompt, ensure_ascii=False, indent=2)}

用户已有的文字口述如下：
{narratives}

请生成引导式回忆问题。
"""

        # -------- 4. 调用 Qwen --------
        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=all_photos,
            model="qwen-vl-max",
            enable_image_input=True
        )

        print("\n📥 ===== RAW QWEN OUTPUT =====")
        print(result)
        print("================================\n")

        # -------- 5. 解析 JSON --------
        try:
            match = re.search(r'\[.*\]', str(result), re.DOTALL)
            questions = json.loads(match.group(0)) if match else []
        except Exception as e:
            print("❌ JSON parse error:", e)
            questions = []

        print("\n✅ ===== PARSED QUESTIONS =====")
        print(json.dumps(questions, ensure_ascii=False, indent=2))
        print("================================\n")

        return jsonify({"questions": questions})

    except Exception as e:
        print("❌ Backend error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/summarize-group-memory', methods=['POST'])
def summarize_group_memory():
    """
    Stage 2:
    基于某一个照片分组内的 QA，
    总结该分组的 Who / When / Where / What / Emotion
    """
    try:
        data = request.get_json()

        group_id = data.get("group_id")
        group_title = data.get("group_title", "")
        qa_pairs = data.get("qa_pairs", [])

        if group_id is None or not qa_pairs:
            return jsonify({
                "summary": {
                    "who": "",
                    "when": "",
                    "where": "",
                    "what": "",
                    "emotion": ""
                }
            })

        # -------- 1. 组织 QA 文本（给模型看的） --------
        qa_text = []
        for i, qa in enumerate(qa_pairs, start=1):
            q = qa.get("question", "").strip()
            a = qa.get("answer", "").strip()
            if q and a:
                qa_text.append(f"{i}. 问题：{q}\n   回答：{a}")

        qa_block = "\n".join(qa_text)

        print("\n📤 ===== GROUP MEMORY INPUT =====")
        print(f"Group {group_id}: {group_title}")
        print(qa_block)
        print("================================\n")

        # -------- 2. System Prompt（非常关键） --------
        system_prompt = """
你是一名记忆研究与人生叙事分析助手。

你的任务是：
基于用户在某一人生阶段（一个照片分组）中的问答内容，
提炼该阶段的关键信息摘要。

请从以下五个维度进行总结：
1. Who：重要人物（不需要列所有人，只保留关键人物）
2. When：时间背景（如人生阶段、时间段）
3. Where：地点或环境（学校、城市、场景）
4. What：核心事件或经历（最有代表性的）
5. Emotion：主要情绪或情感基调

重要约束：
- 只能基于给定问答内容总结
- 不允许编造未出现的信息
- 如果某一维度信息不足，请返回空字符串 ""
- 每个维度用 1–2 句话概括即可
- 使用中文

输出格式（必须严格遵守，只输出 JSON）：

{
  "who": "",
  "when": "",
  "where": "",
  "what": "",
  "emotion": ""
}
"""

        # -------- 3. User Prompt --------
        prompt = f"""
当前照片分组标题：{group_title}

用户在该分组下的问答如下：
{qa_block}

请基于以上内容进行总结。
"""

        # -------- 4. 调用 Qwen（一次即可） --------
        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            model="qwen-max"  # 这里不需要 VL
        )

        print("\n📥 ===== RAW SUMMARY OUTPUT =====")
        print(result)
        print("================================\n")

        # -------- 5. 解析 JSON --------
        summary = {
            "who": "",
            "when": "",
            "where": "",
            "what": "",
            "emotion": ""
        }

        try:
            match = re.search(r'\{.*\}', str(result), re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                for k in summary.keys():
                    if k in parsed and isinstance(parsed[k], str):
                        summary[k] = parsed[k].strip()
        except Exception as e:
            print("❌ Summary parse error:", e)

        print("\n✅ ===== PARSED SUMMARY =====")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("================================\n")

        return jsonify({"summary": summary})

    except Exception as e:
        print("❌ summarize-group-memory error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/summarize-inter-group', methods=['POST'])
def summarize_inter_group():
    """
    Stage 2:
    基于相邻两个分组之间的 inter QA，
    总结一段“叙事过渡 / 转折 / 发展”的简短文字
    """
    try:
        data = request.get_json()

        left_title = data.get("left_group_title", "")
        right_title = data.get("right_group_title", "")
        qa_pairs = data.get("qa_pairs", [])

        if not qa_pairs:
            return jsonify({"text": ""})

        qa_text = []
        for i, qa in enumerate(qa_pairs, start=1):
            q = qa.get("question", "").strip()
            a = qa.get("answer", "").strip()
            if q and a:
                qa_text.append(f"{i}. 问题：{q}\n   回答：{a}")

        qa_block = "\n".join(qa_text)

        system_prompt = """
你是一名人生叙事与记忆结构分析助手。

你的任务是：
基于用户在两个相邻人生阶段之间的问答内容，
总结一段“承上启下”的叙事性过渡文字。

这段文字应当：
- 用于连接前一个阶段与后一个阶段
- 强调变化、转折、发展或情绪流动
- 不重复具体细节
- 不超过 2–3 句话
- 使用中文
- 不编造未出现的信息

输出格式（严格，只输出 JSON）：

{
  "text": ""
}
"""

        prompt = f"""
前一阶段标题：{left_title}
后一阶段标题：{right_title}

用户在这两个阶段之间的问答如下：
{qa_block}

请生成一段简短的阶段过渡总结。
"""

        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            model="qwen-max"
        )

        text = ""
        try:
            match = re.search(r'\{.*\}', str(result), re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                text = parsed.get("text", "").strip()
        except Exception as e:
            print("❌ Inter summary parse error:", e)

        return jsonify({"text": text})

    except Exception as e:
        print("❌ summarize-inter-group error:", e)
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
    """生成视频 Prompt - 支持单张照片的静态视频和照片对的过渡视频，新增主体照片参数"""
    try:
        data = request.get_json()
        p_type = data.get("type", "transition")
        sentence = data.get("sentence", "")
        next_sent = data.get("next_sentence", "")
        photo_pair = data.get("photo_pair", [])  # 原始照片对
        subject_pair = data.get("subject_pair", [])  # 新增：主体照片对
        
        # === 新增：主体照片检查逻辑 ===
        print(f"🔍 [主体照片检查] 收到 {len(subject_pair)} 张主体照片")
        has_valid_subject_photos = False
        valid_subject_paths = []
        
        # 检查主体照片的有效性
        for i, subject_url in enumerate(subject_pair):
            if subject_url:
                print(f"  - 主体照片 {i+1}: {subject_url[:100]}...")
                if subject_url.startswith("data:image"):
                    # 处理 base64 数据
                    try:
                        fname = f"subject_{p_type}_{i}_{uuid.uuid4().hex}.png"
                        subject_path = GENERATED_DIR / fname
                        header, encoded = subject_url.split(",", 1)
                        with open(subject_path, "wb") as f:
                            f.write(base64.b64decode(encoded))
                        valid_subject_paths.append(str(subject_path))
                        has_valid_subject_photos = True
                        print(f"    ✅ 成功保存 base64 主体照片: {fname}")
                    except Exception as e:
                        print(f"    ❌ 处理 base64 主体照片失败: {e}")
                else:
                    # 检查 URL 或本地路径的有效性
                    local_path = _resolve_local_path(subject_url)
                    if local_path and local_path.exists():
                        valid_subject_paths.append(str(local_path))
                        has_valid_subject_photos = True
                        print(f"    ✅ 找到有效主体照片: {local_path.name}")
                    else:
                        print(f"    ⚠️ 主体照片路径无效: {subject_url}")
        
        print(f"🔍 [主体照片检查结果] 有效主体照片: {len(valid_subject_paths)} 张")
        
        # 如果没有主体照片，使用降级方案
        if not has_valid_subject_photos:
            print("⚠️ 警告：没有有效的主体照片，将使用原始照片作为替代")
            # 将原始照片复制到主体照片列表
            for i, photo_url in enumerate(photo_pair):
                local_path = _resolve_local_path(photo_url)
                if local_path and local_path.exists():
                    # 复制原始照片作为主体照片的替代
                    fname = f"subject_fallback_{i}_{uuid.uuid4().hex}{local_path.suffix}"
                    fallback_path = GENERATED_DIR / fname
                    shutil.copy2(local_path, fallback_path)
                    valid_subject_paths.append(str(fallback_path))
                    print(f"    📝 使用原始照片作为主体照片替代: {fname}")
        
        # 如果没有图片，使用原来的文本方式
        if not photo_pair:
            if p_type == "static":
                sys_p = "你是一名影视分镜师。为单张照片生成5秒时长的微动态视频指令。要求：视频时长严格控制在5秒内，描述照片中的静态场景，并添加一些微妙的动态元素，如光影变化、轻微的镜头移动等，让画面生动但不夸张，所有动作必须适应5秒时长。"
                content = f"画面：{sentence}"
            else:
                sys_p = "你是一名专业影视分镜师，精通视频首尾帧过渡效果设计。以图片 1 为视频首帧、图片 2 为尾帧，基于对两张图片内容的理解，生成一段5秒时长的视频制作指令。要求过渡自然流畅，节奏紧凑，确保在5秒内完成完整过渡。"
                content = f"起：{sentence}\n止：{next_sent}"
            result = qwen.get_response(prompt=content, system_prompt=sys_p, model="qwen-max", enable_image_input=False)
            return jsonify({
                "prompt": str(result).strip(),
                "subject_photos_status": {
                    "has_valid_subject_photos": False,
                    "subject_count": 0,
                    "message": "未提供原始照片，仅使用文本生成"
                }
            })
        
        # 使用 analyze_images 分析图片
        try:
            # 1. 将原始照片下载到本地
            temp_images = []
            
            # 处理原始照片
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
                raise Exception("无法获取有效的原始图片")
            
            # 构建用于Qwen分析的完整图片列表（原始+主体）
            all_images_for_analysis = []
            
            if p_type == "static":
                # 静态视频：只需要第一张原始照片和对应的主体
                all_images_for_analysis = [temp_images[0]]
                if len(valid_subject_paths) > 0:
                    all_images_for_analysis.append(valid_subject_paths[0])
                else:
                    all_images_for_analysis.append(temp_images[0])  # 降级方案
                
                # 构建强调5秒时长和主体不变性的prompt
                custom_prompt = f"""
                【视频时长】5秒
                【照片关系】照片2是照片1主体的面部特写，用于身份锁定

                你是一名专业视频动效设计师。基于场景图（照片1）和面部特征（照片2），设计5秒静态转动态视频指令。

                照片描述：{sentence}

                【核心要求】：
                1. **主体锁定**：通过照片2面部特征，在照片1中精准识别核心人物，所有动态围绕该主体展开

                2. **5秒节奏**：
                - 0-0.5秒：细微预备动作
                - 0.5-4.5秒：核心动作展开（符合人物气质）
                - 4.5-5秒：动作收尾与稳定定格

                3. 【以下要求原话保留】
                - 禁止人物替换或突变，5秒内主体身份必须绝对一致
                - **动作表情必须自然符合物理规律** 
                - 禁止突兀跳切、瞬间变化，所有动态必须渐进式

                4. **输出**：描述5秒内主体的视觉变化过程（含时间节点），≤300字，**必须包含"动作表情必须自然符合物理规律"等要求的原句**
                """
            else:
                # 过渡视频：需要两张原始照片和对应的主体
                all_images_for_analysis = [
                    temp_images[0], 
                    valid_subject_paths[0] if len(valid_subject_paths) > 0 else temp_images[0],
                    temp_images[1], 
                    valid_subject_paths[1] if len(valid_subject_paths) > 1 else temp_images[1]
                ]
                
                # 构建强调5秒时长和主体不变性的prompt
                custom_prompt = f"""
【主体照片说明】：
- 照片2 = 第一张照片（照片1）中主体的面部特写
- 照片4 = 第二张照片（照片3）中主体的面部特写
- 照片2与照片实际上是同一人，只是状态/角度/年龄不同，然后你需要识别照片2和照片4在各自图片1和图片3中对应的位置，身体形态，穿着等重要元素，并在生成视频指令描述中我也要提到这个主体的面部、衣服、身体形态等特征，谁是主体由谁转换到谁。

你是一名专业的视频过渡效果设计师。请基于两张完整场景（照片1、3）和对应的面部特写（照片2、4），设计一段5秒时长的主体连贯过渡效果。

【核心要求 - 主体连贯性（最重要）】：
1. **主体身份锁定**：照片2和照片4所在的人物为各自照片的主体。然后你需要识别照片2和照片4在各自图片1和图片3中对应的位置，身体形态，穿着等重要元素，并在生成视频指令描述中我也要提到这个主体的面部、衣服、身体形态等特征，谁是主体由谁转换到谁。
2. **强制主体过渡**：视频必须清晰展现"照片2的主体"自然转化为"照片4的主体"，这是视频的核心叙事线索
3. **禁止主体突变**：严禁出现主体人物突然切换、替换或消失的情况，主体必须在5秒内保持视觉连续性

【5秒过渡节奏设计】：
- 0-1秒：首帧稳定，主体开始细微动作
- 1-3.5秒：**核心过渡阶段**，主体姿态/表情/角度从照片2状态向照片4状态自然演变，背景同步渐变。注意设计不得背景突然变换，强调主体动作和背景平滑过渡
- 3.5-5秒：过渡完成，主体定格为照片4状态，与尾帧无缝衔接

【禁止事项】：这些禁止事项我想在生成的指令中原话提到！
❌ 禁止突然的场景切换或跳切，必须是要主体的转场过渡
❌ 禁止主体人物在过渡中突然改变身份或消失
❌ 禁止背景与主体动作脱节
❌ 禁止机械式转场（如淡入淡出、滑动切换）替代主体动态演变

【强制要求】：
✓ 主体必须在5秒内完成从照片2到照片4的自然演变。然后你需要识别照片2和照片4在各自图片1和图片3中对应的位置，身体形态，穿着等重要元素，并在生成视频指令描述中我也要提到这个主体的面部、衣服、身体形态等特征，谁是主体由谁转换到谁。
✓ 背景变化必须与主体动作节奏完全同步
✓ 所有变化必须是渐进、连贯、可感知的，动作表情自然符合物理规律，这在指令中要明确提出，不得突然变化场景！

输出要求：详细描述5秒内"主体演变+场景过渡"的完整过程，强调主体连贯性，400字以内
"""
            
            # 调用 analyze_images 分析所有图片
            result = analyze_images(all_images_for_analysis, custom_prompt)
            
            # 3. 清理临时文件
            for img_path in temp_images:
                if img_path.startswith(str(GENERATED_DIR)) and 'temp_' in img_path:
                    try:
                        os.unlink(img_path)
                    except:
                        pass
            
            for img_path in valid_subject_paths:
                if img_path.startswith(str(GENERATED_DIR)) and ('subject_' in img_path or 'subject_fallback_' in img_path):
                    try:
                        os.unlink(img_path)
                    except:
                        pass
            
            if result:
                return jsonify({
                    "prompt": result.strip(),
                    "subject_photos_status": {
                        "has_valid_subject_photos": has_valid_subject_photos,
                        "subject_count": len(valid_subject_paths),
                        "message": "主体照片已成功处理" if has_valid_subject_photos else "使用原始照片作为主体照片替代"
                    }
                })
            else:
                raise Exception("未能从 analyze_images 获取有效结果")
            
        except Exception as img_error:
            print(f"analyze_images 失败: {img_error}")
            # 降级使用原来的文本方式
            if p_type == "static":
                sys_p = "你是一名影视分镜师。为单张照片生成5秒时长的微动态视频指令。要求动作节奏紧凑，适合5秒时长。"
                content = f"画面：{sentence}"
            else:
                sys_p = "你是一名影视分镜师。为两张照片生成5秒时长的平滑过渡视频指令。要求过渡自然流畅，节奏紧凑。"
                content = f"起：{sentence}\n止：{next_sent}"
            result = qwen.get_response(prompt=content, system_prompt=sys_p, model="qwen-max", enable_image_input=False)
            return jsonify({
                "prompt": str(result).strip(),
                "subject_photos_status": {
                    "has_valid_subject_photos": False,
                    "subject_count": 0,
                    "message": "图片分析失败，使用文本降级方案"
                }
            })
            
    except Exception as e:
        print("refine-prompt error:", e)
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

@app.route('/video-file-status')
def video_file_status():
    # 使用固定的视频路径
    video_path = Path("static/video/generated_video.mp4")
    
    response = {
        'fileExists': False,
        'fileSize': 0,
        'lastModified': None,
        'videoUrl': '/static/video/generated_video.mp4',
        'isCompleted': False,
        'error': None
    }
    
    try:
        if video_path.exists():
            stat = video_path.stat()
            response.update({
                'fileExists': True,
                'fileSize': stat.st_size,
                'lastModified': stat.st_mtime,
            })
            
            # 更严格的完成判断：文件大小稳定且大于一定值
            if stat.st_size > 10 * 1024 * 1024:  # 10MB以上认为可能完成
                # 检查文件是否在最近10秒内没有修改（表示生成完成）
                current_time = time.time()
                if current_time - stat.st_mtime > 10:  # 10秒内无修改
                    response['isCompleted'] = True
                
    except Exception as e:
        response['error'] = str(e)
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)