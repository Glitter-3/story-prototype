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
from typing import Optional, List

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
    强力解析本地路径：
    无论传入的是 http://.../static/generated/abc.jpg
    还是 /static/uploads/abc.jpg
    都通过提取文件名来去硬盘里找文件。
    """
    if not url or not isinstance(url, str):
        return None
    if url.startswith("data:"):
        return None  # 已经是 base64 data uri

    if base_dirs is None:
        base_dirs = [GENERATED_DIR, UPLOADS_DIR]  # 优先找生成的图

    # 1. 提取文件名 (忽略路径前缀)
    try:
        parsed = urlparse(unquote(url))
        fname = os.path.basename(parsed.path)  # 只取 abc.jpg
        if not fname or '.' not in fname:
            return None
    except Exception:
        return None

    # 2. 在所有目录里查找这个文件名
    for base in base_dirs:
        candidate = base / fname
        if candidate.is_file():
            return candidate

    # 3. 如果没找到，尝试 fallback 扩展名 (jpg <-> png 等)
    stem, ext = os.path.splitext(fname)
    ext = ext.lower()
    alternatives = ['.jpg', '.jpeg', '.png', '.webp']
    for alt_ext in alternatives:
        if alt_ext == ext:
            continue
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

import os
import re
import json
import traceback
import logging
from flask import request, jsonify


# 确保 logger 可用
logger = logging.getLogger(__name__)

@app.route('/generate-questions', methods=['POST'])
def generate_questions():
    """Stage 2: 事实性提问 (Priority 2)"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        photos = data.get('photos', [])
        narratives = data.get('narratives', '')

        system_prompt = """
            你是一名专业的纪录片导演兼视觉档案员。
            任务：根据照片和文字，生成帮助用户还原客观场景细节的问题。
            严禁行为：禁止询问情感、意义、心情。
            提问原则：
            1. 聚焦视觉事实（时间、地点、物体、穿搭、天气）。
            2. 挖掘画面外信息。
            3. 确认模糊细节。
            输出：JSON 数组 [{"text": "...", "answer": "", "answered": false, "showInput": false}]
            """
        prompt = f"用户文字：\n{narratives}\n请结合图片生成事实性问题。"

        # 调用模型（按你原有方式）
        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            image_path_list=photos,
            model="qwen-vl-max",
            enable_image_input=True
        )

        # 尝试从模型返回中提取 JSON 数组
        questions = []
        raw_text = str(result)
        try:
            # 优先尝试直接解析整个返回（如果 result 已经是 dict/list）
            if isinstance(result, (list, dict)):
                questions = result if isinstance(result, list) else result.get("questions", [])
            else:
                # 找到第一个看起来像 JSON 数组的内容并解析
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if match:
                    questions = json.loads(match.group(0))
                else:
                    # 有时返回是单纯的 JSON 字符串
                    try:
                        parsed = json.loads(raw_text)
                        questions = parsed if isinstance(parsed, list) else parsed.get('questions', [])
                    except Exception:
                        questions = []
        except Exception as parse_ex:
            # 解析出错，记录日志并保留 raw_text 以便前端或调试使用
            logger.exception("Failed to parse model response: %s", parse_ex)
            questions = []

        # 如果解析失败但想回传原始文本以便调试：可以把 raw 也返回
        return jsonify({"questions": questions, "raw": raw_text})

    except Exception as e:
        # 获取完整 traceback 字符串
        tb = traceback.format_exc()

        # 是否允许在响应中返回详细错误（优先级：config -> env var -> app.debug）
        show_detailed = app.config.get('SHOW_DETAILED_ERRORS',
                       os.environ.get('SHOW_DETAILED_ERRORS', str(app.debug)).lower() in ('1','true','yes'))

        # 记录到服务器日志（始终记录）
        logger.error("Unhandled exception in /generate-questions: %s\n%s", e, tb)

        if show_detailed:
            # 开发/调试模式：返回详细信息（注意安全）
            return jsonify({
                "error": str(e),
                "exception_type": type(e).__name__,
                "traceback": tb
            }), 500
        else:
            # 生产安全模式：只返回简要信息并把详细信息记录到日志
            return jsonify({
                "error": "Internal Server Error",
                "message": str(e)
            }), 500


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
            你是一名视觉侦探。任务：对比“用户故事”与“AI生成的画面”，找出不一致或潜在线索。
            核心策略：【猜测 + 求证】
            不要问宽泛的“你想到什么？”，必须结合图片元素提出假设。
            例如：
            - "AI生成的图片背景有座灯塔，当时岸边是否有这样的建筑？"
            - "图中大家在奔跑，这是否就是你提到的那场大雨？"
            
            输出格式：JSON 数组 [{"text": "...", "answer": "", "answered": false, "showInput": false}]
            """
        prompt = f"故事：\n{narrative}\n\n请结合参考图片提出猜测性问题。"
        
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
    """生成视频 Prompt"""
    try:
        data = request.get_json()
        p_type = data.get("type", "transition")
        sentence = data.get("sentence", "")
        next_sent = data.get("next_sentence", "")
        
        if p_type == "static":
            sys_p = "你是一名影视分镜师。为单张照片生成15字以内的微动态视频指令（如：微风吹拂，镜头推进）。"
            content = f"画面：{sentence}"
        else:
            sys_p = "你是一名影视分镜师。为两张照片生成15字以内的平滑过渡视频指令。"
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
        cmd = ["python", "generate.py", "--photos", *local_paths, "--prompts", *[str(p) for p in prompts], "--output", str(out_path)]
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

