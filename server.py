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


def base64_to_file(b64_or_dataurl: str, filename=None) -> str:
    """
    将 base64（或 data:image/...）保存为本地文件，返回文件路径
    """
    if b64_or_dataurl.startswith("data:image"):
        b64 = b64_or_dataurl.split(",", 1)[1]
        mime = re.match(r"data:(image/\w+);base64", b64_or_dataurl).group(1)
        ext = mime.split("/")[-1]
    else:
        b64 = b64_or_dataurl
        ext = "jpg"

    if not filename:
        filename = f"{uuid.uuid4().hex}.{ext}"

    out_path = GENERATED_DIR / filename
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64))

    return str(out_path)


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

import tempfile
import shutil

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
        你的任务分两步：
        第一步：是对这些照片按**时间顺序**划分为若干组（每组代表一个阶段或事件），并为每组起一个简短的时间阶段名称（如“童年时期”、“大学时光”、“疫情居家”等）。
        第二步：在每一个时间阶段内部，如果包含多张照片，请根据人物、地点、事件或情感的差异，将其进一步划分为若干“子分组”。

        要求：
        1. 每张照片只能属于一个子分组。
        2. 每个子分组语义上应当是一个完整事件或场景。
        3. 如果某个时间阶段内只有一张照片，则只生成一个子分组。
        4. 大分组按时间从前到后排序。
        5. 输出严格为 JSON 格式，结构如下：
        {
            "groups": [
                {
                "name": "阶段名称",
                "subgroups": [
                    {
                    "name": "子分组名称",
                    "photo_indices": [0, 1]
                    }
                ]
                }
            ]
        }      
        6. 如果无法判断时间顺序，请按上传顺序分组，每张照片一组。
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
            for sg in g.get("subgroups", []):
                all_photos.extend(sg.get("photos", []))


        # -------- 2. 给模型看的分组结构（只含语义） --------
        groups_for_prompt = []
        for g in photo_groups:
            groups_for_prompt.append({
                "group_id": g["group_id"],
                "group_title": g.get("name", ""),
                "subgroups": [
                    {
                        "subgroup_id": sg["subgroup_id"],
                        "title": sg.get("name", ""),
                        "photo_count": len(sg.get("photos", []))
                    }
                    for sg in g.get("subgroups", [])
                ]
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
基于【照片的层级结构（时间阶段 → 事件子分组）】、【照片内容】以及【已有文字口述】，生成有助于用户回忆与讲述人生故事的引导式问题。

一、结构说明（非常重要）

- 每一个 group 表示一个“时间阶段”
- 每一个 subgroup 表示该时间阶段中的一个“具体事件或片段”
- 组内问题（intra）必须严格针对某一个 subgroup
- 组间问题（inter）用于连接两个相邻 group（时间阶段）

二、问题类型

1. 组内提问（type = "intra"）
- 针对单个 subgroup
- 提问维度可参考：
  人物（Who）、时间（When）、地点（Where）、事件（What）、情感与感受
- 并非每个维度都必须提问
- 每个subgroup都要提问，对每个subgroup提出你认为“最关键、最有价值”的 2–3 个问题

2. 组间提问（type = "inter"）
- 针对两个相邻的 group
- 不重复具体照片细节
- 重点关注人生阶段之间的动因、转折、选择、影响或内在变化

三、重要约束

- 必须按时间顺序输出问题，一个阶段提问完再进入下一个阶段，不要跳跃或反复：
  group 0 的 subgroup → group 0 & 1 的 inter →
  group 1 的 subgroup → group 1 & 2 的 inter → …
- 你需要根据具体照片内容与分组主题自行判断：
  是否需要提问、问什么、问多少
- 总共提出至少 8 个问题
- 提问的答案汇总起来得到的信息需要能完整连缀整个故事，明确回答人物（Who）、时间（When）、地点（Where）、事件（What）、情感与感受。

四、输出格式（必须严格遵守，只输出 JSON 数组）

每个元素结构如下：

{
  "type": "intra" | "inter",

  "group_id": number | null,
  "subgroup_id": number | null,

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
  - subgroup_id 必须填写
  - left_group_id 与 right_group_id 必须为 null

- 如果 type = "inter"：
  - group_id 与 subgroup_id 必须为 null
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


@app.route('/summarize-subgroup-memory', methods=['POST'])
def summarize_subgroup_memory():
    """
    Stage 2:
    基于某一个照片分组内的 QA，
    总结该分组的 Who / When / Where / What / Emotion
    """
    try:
        data = request.get_json()
        print("Received summarize-subgroup-memory request:", data)

        group_id = data.get("group_id")
        group_title = data.get("group_title", "")
        qa_pairs = data.get("qa_pairs", [])

        if group_id is None or not qa_pairs:
            print("⚠️ Missing group_id or empty qa_pairs.")
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
基于用户在【某一个具体事件（subgroup）】中的问答内容，
提炼该阶段的关键信息摘要。

背景说明：
- 该事件隶属于某一个时间阶段（group）
- 如果问答中没有提供更精确的时间信息，则 When 可以使用该时间阶段的标题作为默认时间背景

请从以下五个维度进行总结：
1. Who：关键人物（与用户关系、身份）
2. When：时间背景（如人生阶段、时间段）
3. Where：地点或环境（学校、城市、场景）
4. What：核心事件或经历
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
    """
    Stage 3:
    将 Stage 2 产生的结构化记忆（group / subgroup / inter-group）
    整合为一篇连贯的第一人称叙事文本
    """
    try:
        data = request.get_json()

        group_memories = data.get('group_memories', {})
        subgroup_memories = data.get('subgroup_memories', {})
        inter_group_memories = data.get('inter_group_memories', {})

        system_prompt = """
你是一个叙事作家。
任务：根据用户已经整理好的阶段记忆与事件记忆，
将其整合为一篇连贯、自然、第一人称的人生叙事文本。

要求：
1. 严格基于提供的结构化信息，不编造事实
2. 合理组织时间顺序
3. 自然融入情绪（emotion）
4. 使用过渡文本连接不同阶段
5. 只输出最终整合后的全文
"""

        prompt = f"""
【阶段记忆（Group Summaries）】
{group_memories}

【事件记忆（Subgroup Summaries）】
{subgroup_memories}

【阶段过渡（Inter-group Transitions）】
{inter_group_memories}

请根据以上信息，写出一篇完整的第一人称叙事文本：
"""

        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            model="qwen-vl-max",
            enable_image_input=False
        )

        return jsonify({"integrated_text": str(result).strip()})

    except Exception as e:
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
        subgroup_summaries = data.get('subgroup_summaries', {})
        subgroup_context = data.get('subgroup_context', None)
        style_tags = data.get('style_tags', {})  # 新增：按 subgroup 的风格描述
        
        # 【新增】根据 subgroup_context 调整提示词
        if subgroup_context:
            # ====== subgroup 模式：更具体的提示 ======
            system_prompt_1 = """
            你是一个叙事视觉设计助手。任务：将文本转化为分镜式 Prompt 序列。
            
            【核心规则：视觉场景合并 (Visual Scene Merging)】
            1. **必须合并**：连续的句子如果描述的是同一个静止画面、同一个动作的持续状态、或者对同一场景的细节/心理补充，**必须合并为一个 Prompt**。
            - 例子："我坐在船头。" + "风吹过我的头发。" + "心情很舒畅。" -> 合并为一句。
            2. **切分条件**：只有当发生以下情况时才开启新 Prompt：
            - 明确的时间跳跃。
            - 地点的物理转换。
            - 视觉主体的根本改变。
            
            【特别说明】
            你正在处理的是一个特定事件子分组（subgroup）的文本。
            请确保生成的分镜与该子分组的主题和内容高度相关，不要生成与该子分组无关的分镜。
            在大多数情况下，这段文本只应对应 1–2 个核心画面。除非发生明确的时间或地点跃迁，否则不要主动拆分为多个分镜。
            
            【Prompt 规范】
            - 包含：主体、动作、环境（含时代/地域特征）、光影氛围。
            - 约 20 字。
            - 必须具体可画，避免抽象形容词。
            
            【输出格式】
            JSON 数组：[{"sentence": "合并后的原句片段", "prompt": "画面描述"}]
            注意："sentence" 字段应当包含该画面对应的所有原文句子，以便后续追踪。
            """
        else:
            # ====== 全局模式：原有提示 ======
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
        response_1 = qwen.get_response(
            prompt=prompt_1,
            system_prompt=system_prompt_1,
            model="qwen-vl-max",
            enable_image_input=False
        )
        system_prompt_2 = """
        你是一个记忆结构对齐助手。

        任务：
        将“叙事分镜句子”映射到最合适的事件子分组（subgroup）。

        已知信息：
        - 用户已经在 Stage 2 中，人工整理了事件子分组（subgroup）
        - 每个 subgroup 描述的是一个明确的事件 / 场景 / 时间段
        - 下面提供的 sentence，是整合叙事后拆分出的画面级描述

        规则：
        1. 每个 sentence **必须且只能**归属到一个 subgroup
        2. 归属依据是：事件一致性、时间、人物、地点、行为
        3. 不要创建新 subgroup，只能从给定列表中选择
        4. 如果多个 subgroup 都可能，选择“最具体、最贴近”的那个

        输出格式（严格 JSON）：
        [
        {
            "sentence_index": 0,
            "group_index": gIdx,
            "subgroup_index": sgIdx
        }
        ]
        """

        subgroup_desc = []
        for gIdx, subgroups in subgroup_summaries.items():
            for sgIdx, sg in subgroups.items():
                data = sg.get("data", {})
                subgroup_desc.append({
                    "group_index": gIdx,
                    "subgroup_index": sgIdx,
                    "who": data.get("who"),
                    "when": data.get("when"),
                    "where": data.get("where"),
                    "what": data.get("what"),
                    "emotion": data.get("emotion")
                })

        try:
            text_output = response_1 if isinstance(response_1, str) else response_1.get("output", {}).get("text", "")
            match = re.search(r'\[.*\]', text_output, re.DOTALL)
            qwen_sentences = json.loads(match.group(0)) if match else []
        except:
            print("Prompt生成JSON解析失败，降级处理")
            qwen_sentences = [{"sentence": narratives, "prompt": narratives}]

        # ===== 新增 ①：构造 align_prompt 并请求对齐 =====
        align_prompt = f"""
        【事件子分组列表】
        {subgroup_desc}

        【叙事分镜句子】
        {[{"index": i, "sentence": s["sentence"]} for i, s in enumerate(qwen_sentences)]}

        请完成 sentence 到 subgroup 的映射：
        """

        align_resp = qwen.get_response(
            prompt=align_prompt,
            system_prompt=system_prompt_2,
            model="qwen-vl-max",
            enable_image_input=False
        )

        try:
            align_json = json.loads(
                re.search(r'\[.*\]', str(align_resp), re.DOTALL).group(0)
            )
        except:
            align_json = []

        sentence_to_subgroup = {
            item["sentence_index"]: (item["group_index"], item["subgroup_index"])
            for item in align_json
        }
        # ===== 新增结束 =====

        # Photo-Sentence Matching
        sentence_pairs = []
        matched_indices = set()

        if photos:
            for photo_idx, photo in enumerate(photos):
                all_sents = "\n".join(
                    [f"{i}. {item['sentence'][:30]}..." for i, item in enumerate(qwen_sentences)]
                )
                match_prompt = f"图片与以下哪个片段最匹配？返回索引JSON [{{'index': i, 'score': s}}]\n{all_sents}"

                try:
                    match_res = qwen.get_response(
                        prompt=match_prompt,
                        image_path_list=[photo],
                        model="qwen-vl-max",
                        enable_image_input=True
                    )
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

                sentence_pairs.append({
                    "index": photo_idx + 1000,
                    "photo": photo,
                    "sentence": None,
                    "prompt": None
                })

        # ===== 新增 ②：在补全文本 sentence 时注入 group / subgroup =====
        for idx, item in enumerate(qwen_sentences):
            if idx not in matched_indices:
                gIdx, sgIdx = sentence_to_subgroup.get(idx, (None, None))
                # 注入风格描述到 prompt
                base_prompt = item["prompt"]
                style_key = f"{gIdx}_{sgIdx}"
                if style_tags.get(style_key):
                    enhanced_prompt = f"{base_prompt}. Photography style: {style_tags[style_key]}."
                else:
                    enhanced_prompt = base_prompt
                sentence_pairs.append({
                    "index": idx,
                    "photo": None,
                    "sentence": item["sentence"],
                    "prompt": enhanced_prompt,
                    "group_index": gIdx,
                    "subgroup_index": sgIdx
                })
        # ===== 新增结束 =====

        sentence_pairs.sort(key=lambda x: x['index'])
        return jsonify({"sentence_pairs": sentence_pairs})

    except Exception as e:
        print("generate-prompts error:", e)
        return jsonify({"error": str(e)}), 500
    


@app.route('/analyze-photo-style', methods=['POST'])
def analyze_photo_style():
    """
    Stage 3: 按 subgroup 分析原始照片的视觉风格，生成英文风格描述 tag。
    输入：{ "subgroups": [{ "group_index": 0, "subgroup_index": 0, "photos": ["base64..."] }] }
    输出：{ "style_tags": { "0_0": "warm amber tones, ..." } }
    """
    try:
        data = request.get_json()
        subgroups = data.get('subgroups', [])
        style_tags = {}

        style_analysis_system = (
            "You are a professional photography style analyst. "
            "Analyze the overall visual style of the provided photos and output a concise English style description (40-60 words). "
            "Cover these 6 dimensions: color tone, exposure/contrast, texture/film grain, lighting, shooting style, and overall mood. "
            "Output ONLY the descriptive phrases separated by commas. No explanations, no JSON, no extra text."
        )

        for sg_item in subgroups:
            gIdx = sg_item.get('group_index')
            sgIdx = sg_item.get('subgroup_index')
            photos_b64 = sg_item.get('photos', [])

            key = f"{gIdx}_{sgIdx}"

            if not photos_b64:
                print(f"[analyze-photo-style] subgroup {key} 无照片，跳过")
                continue

            # 把 base64 列表保存为临时文件，供 qwen 调用
            tmp_paths = []
            try:
                for i, b64str in enumerate(photos_b64[:4]):  # 最多取 4 张
                    # 支持 data:image/... 前缀
                    if ',' in b64str:
                        b64str = b64str.split(',', 1)[1]
                    fname = f"style_analysis_{gIdx}_{sgIdx}_{i}_{uuid.uuid4().hex[:6]}.jpg"
                    tmp_path = GENERATED_DIR / fname
                    with open(tmp_path, 'wb') as f:
                        f.write(base64.b64decode(b64str))
                    tmp_paths.append(str(tmp_path))

                style_prompt = (
                    "Please analyze the visual style of these photos. "
                    "Output 40-60 English words covering: color tone, exposure/contrast, "
                    "texture/film grain, lighting quality, shooting style, and mood. "
                    "Use comma-separated phrases only."
                )

                result = analyze_images(tmp_paths, prompt=style_prompt, system_prompt=style_analysis_system)

                if result:
                    # 清理多余换行和引号
                    tag = result.strip().strip('"').replace('\n', ', ')
                    style_tags[key] = tag
                    print(f"[analyze-photo-style] subgroup {key} → {tag[:80]}...")
                else:
                    print(f"[analyze-photo-style] subgroup {key} 分析返回空，跳过")

            except Exception as e:
                print(f"[analyze-photo-style] subgroup {key} 分析失败: {e}")
            finally:
                # 清理临时文件
                for p in tmp_paths:
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        return jsonify({"style_tags": style_tags})

    except Exception as e:
        print("analyze-photo-style error:", e)
        return jsonify({"style_tags": {}}), 200  # 静默降级，不返回 500


@app.route('/generate-images', methods=['POST'])
def generate_images():
    try:
        payload = request.get_json()
        pairs = payload.get("sentence_pairs", [])
        if not pairs:
            return jsonify({"error": "no sentence_pairs"}), 400

        # === 初始化生成器 ===
        multi_ig = MultiImage2Image()
        token = multi_ig._encode_jwt_token()

        HEADERS = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        def extract_base64(dataurl_or_b64: str) -> str:
            """兼容 data:image/... 与纯 base64"""
            if dataurl_or_b64.startswith("data:image"):
                return dataurl_or_b64.split(",", 1)[1]
            return dataurl_or_b64

        def process_single_pair(item):
            idx = item.get("index", 0)
            prompt = item.get("prompt")

            # ✅ 结构字段（仅透传）
            group_index = item.get("group_index")
            subgroup_index = item.get("subgroup_index")

            if not prompt:
                return {
                    "index": idx,
                    "prompt": None,
                    "generated_urls": [],
                    "group_index": group_index,
                    "subgroup_index": subgroup_index,
                    "note": "no prompt"
                }

            photo_list = item.get("photo", [])
            if not photo_list:
                return {
                    "index": idx,
                    "prompt": prompt,
                    "generated_urls": [],
                    "group_index": group_index,
                    "subgroup_index": subgroup_index,
                    "error": "No reference photos provided"
                }

            # 角色裁剪头像列表（主体参考图），由前端传入，纯 base64 字符串
            character_avatars = item.get("character_avatars", [])  # list of pure-base64 strings
            # Stage1 第一张原图（风格参考图），纯 base64 字符串或 None
            style_photo = item.get("style_photo", None)

            try:
                generated_urls = []

                # ——— 决策：主体参考图 ———
                # 优先使用角色面板裁剪头像（1–4 张），无则回退到 subgroup 原图
                if character_avatars:
                    # 最多 4 张，直接是纯 base64，不需要 extract_base64
                    subject_imgs = [
                        {"subject_image": b64}
                        for b64 in character_avatars[:4]
                    ]
                    print(f"[generate-images idx={idx}] 使用角色裁剪头像 {len(subject_imgs)} 张作为 subject_image_list")
                else:
                    # 回退：用 subgroup 原图，最多 4 张
                    proc_photos = photo_list[:4]
                    subject_imgs = [
                        {"subject_image": extract_base64(img)}
                        for img in proc_photos
                    ]
                    print(f"[generate-images idx={idx}] 无角色头像，回退为 subgroup 原图 {len(subject_imgs)} 张")

                # ——— 决策：风格参考图 ———
                # 使用 Stage1 第一张原图（已由前端转成纯 base64）
                style_img = style_photo if style_photo else None

                # ——— API 约束：styleImage + sceneImage + subjectImageList 总数 >= 2 ———
                # 如果 subject 只有 1 张且没有 style_img，API 会报 1201 错误
                # 兜底方案：把 photo_list 第一张原图作为 style_img 补充
                total_ref_count = len(subject_imgs) + (1 if style_img else 0)
                if total_ref_count < 2:
                    fallback_style = extract_base64(photo_list[0]) if photo_list else None
                    if fallback_style:
                        style_img = fallback_style
                        print(f"[generate-images idx={idx}] ⚠️ 总参考图不足2张，自动用原图补充 style_image")

                # ——— 打印本次生成依赖的参考图信息，便于调试 ———
                print(f"\n{'='*60}")
                print(f"[generate-images idx={idx}] 🎨 生成参数摘要")
                print(f"  prompt: {prompt[:80]}{'...' if len(prompt)>80 else ''}")
                print(f"  风格参考图 (style_image): {'有 ✅' if style_img else '无 ❌'}")
                print(f"  主体参考图 (subject_image_list): {len(subject_imgs)} 张")
                for i, s in enumerate(subject_imgs):
                    b64_preview = list(s.values())[0][:30] if s else ''
                    print(f"    [{i+1}] {b64_preview}...")
                print(f"  原始 photo_list 数量: {len(photo_list)}")
                print(f"  总参考图数量 (style+subject): {(1 if style_img else 0) + len(subject_imgs)}")
                print(f"{'='*60}\n")

                task_result = multi_ig.run(
                    subject_imgs=subject_imgs,
                    headers=HEADERS,
                    prompt=prompt,
                    style_img=style_img,
                    model_name="kling-v2",
                    n=1,
                    aspect_ratio="3:4",
                    max_wait=300,
                    interval=5
                )

                imgs = (
                    task_result
                    .get("data", {})
                    .get("task_result", {})
                    .get("images", [])
                    or []
                )

                for im in imgs:
                    remote_url = im.get("url")
                    if remote_url:
                        local_url = download_to_generated(remote_url)
                        if local_url:
                            generated_urls.append(local_url)

                return {
                    "index": idx,
                    "prompt": prompt,
                    "generated_urls": generated_urls,
                    "group_index": group_index,
                    "subgroup_index": subgroup_index
                }

            except Exception as e:
                print(f"❌ generate-images failed for idx {idx}: {e}")
                return {
                    "index": idx,
                    "prompt": prompt,
                    "generated_urls": [],
                    "group_index": group_index,
                    "subgroup_index": subgroup_index,
                    "error": str(e)
                }

        # === 并发执行 ===
        results = [None] * len(pairs)
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(process_single_pair, item): i
                for i, item in enumerate(pairs)
            }
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
            你是一名专业的“记忆引导型叙事助理”。
            你的职责不是评判图片是否准确，
            而是帮助用户【借助当前画面，回忆当时未被拍下、未被记录、但真实发生过的部分】。

            重要背景：
            - 你看到的图片（原始照片或 AI 生成图像）只是记忆的触发线索，而不是事实本身。
            - 图片中可能存在偏差、遗漏或错误，这些都应被视为“回忆入口”，而非需要纠正的问题。
            - 提供给你的文字是该场景当前已有的叙事草稿，可能是不完整的。

            你的目标：
            围绕这一具体场景，提出 **不超过 4 个** 高质量问题，
            帮助用户补充画面之外的细节与主观体验，使记忆逐渐脱离对图像本身的依赖。

            提问优先级（由高到低，必须严格遵循）：

            【第一优先级：画面之外的存在】
            - 当时是否还有未出现在画面中的人物？
            - 是否存在声音、对话、气味、环境氛围等非视觉信息？
            - 是否有正在发生、但未被拍下的事件或互动？

            【第二优先级：主观体验与情绪】
            - 当时你内心最强烈或最复杂的感受是什么？
            - 有没有某个瞬间、念头或细节，后来经常被你反复想起？
            - 这一刻在当时是否具有某种特殊意义，但当下并未意识到？

            严格要求：
            1. 不要询问“画得对不对”“是否真实还原”等校对型问题。
            2. 即使图片明显与事实不符，也只能将其作为回忆触发点，而不能要求用户纠正图片。
            3. 每个问题必须是具体、可回答的，避免抽象泛问。
            4. 所有问题都应明确指向“当时发生了什么 / 你感受到了什么”，而不是“现在你怎么看”。

            输出格式要求：
            - 使用中文
            - 严格输出 JSON 数组
            - 每个元素格式如下：

            [
            {
                "text": "问题内容",
                "answer": "",
                "answered": false,
                "showInput": false
            }
            ]

            禁止输出任何解释性文字。

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

# @app.route('/update-text', methods=['POST'])
# def update_text():
#     """
#     Stage 4: 文本更新 (In-place Rewriting)
#     """
#     try:
#         data = request.get_json()
#         current_narrative = data.get('current_narrative', '')
#         new_qa_pairs = data.get('new_qa_pairs', [])
#         if not new_qa_pairs: return jsonify({"updated_text": current_narrative})

#         qa_text = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in new_qa_pairs])

#         system_prompt = """
#         你是一个专业的叙事编辑。
#         你的任务是：将“新补充的问答细节”完美融合进“当前故事草稿”中，形成一篇连贯的完整故事。

#         核心要求：
#         1. **显式标记新增内容**：你必须把所有**基于Q&A新加入的细节、句子或对原句的重大修改**，用 `[NEW]` 和 `[/NEW]` 标签包裹起来。
#            例如：那天天气很好，[NEW]阳光透过树叶洒在地上，像金色的碎片，[/NEW]我们心情都很不错。
#         2. **深度融合**：将新信息插入到故事最合适的逻辑位置，不要只是堆砌在文末。
#         3. **保持连贯**：确保未修改的部分和新加入的部分衔接自然。
#         4. **只输出正文**：不要包含任何解释性语言。
#         """
        
#         prompt = f"现有文章：\n{current_narrative}\n\n补充信息：\n{qa_text}\n\n请输出修改后的完整文章："

#         result = qwen.get_response(prompt=prompt, system_prompt=system_prompt, model="qwen-vl-max", enable_image_input=False)
#         return jsonify({"updated_text": str(result).strip()})

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
@app.route('/update-text', methods=['POST'])
def update_text():
    """
    Stage 4: 文本更新 (In-place Rewriting)
    """
    try:
        data = request.get_json()
        current_narrative = data.get('current_narrative', '')
        new_qa_pairs = data.get('new_qa_pairs', [])
        subgroup_context = data.get('subgroup_context', None)
        
        if not new_qa_pairs:
            return jsonify({"updated_text": current_narrative})
        
        qa_text = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in new_qa_pairs])
        
        # 【新增】判断是否是 subgroup 模式
        if subgroup_context:
            # ====== subgroup 模式：只生成新增的句子 ======
            system_prompt = """
            你是一个专业的叙事补充助手。
            你的任务是：基于用户的问答，生成一段**新增的补充文本**，用于丰富当前的叙事。
            要求：
            1. 只输出新增的补充文本，不要包含原有内容
            2. 补充内容应当与当前叙事风格一致
            3. 不要重复或改写当前叙事中已经出现的句子
            4. 只输出正文，不要包含任何解释性语言
            5. 使用中文
            """
            prompt = f"""当前叙事：
{current_narrative}

补充信息：
{qa_text}

请生成一段新增的补充文本："""
        else:
            # ====== 全局模式：返回完整文本 ======
            system_prompt = """
            你是一个专业的叙事编辑。
            你的任务是：将"新补充的问答细节"完美融合进"当前故事草稿"中，形成一篇连贯的完整故事。
            核心要求：
            1. **显式标记新增内容**：你必须把所有**基于Q&A新加入的细节、句子或对原句的重大修改**，用 `[NEW]` 和 `[/NEW]` 标签包裹起来。
            例如：那天天气很好，[NEW]阳光透过树叶洒在地上，像金色的碎片，[/NEW]我们心情都很不错。
            2. **深度融合**：将新信息插入到故事最合适的逻辑位置，不要只是堆砌在文末。
            3. **保持连贯**：确保未修改的部分和新加入的部分衔接自然。
            4. **只输出正文**：不要包含任何解释性语言。
            5. 使用中文
            """
            prompt = f"""现有文章：
{current_narrative}

补充信息：
{qa_text}

请输出修改后的完整文章："""
        
        result = qwen.get_response(
            prompt=prompt,
            system_prompt=system_prompt,
            model="qwen-vl-max",
            enable_image_input=False
        )
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
    """生成视频 Prompt - 支持单张照片的静态视频和照片对的过渡视频，新增主体照片参数。强制要求有照片输入。"""
    try:
        data = request.get_json()
        p_type = data.get("type", "transition")
        sentence = data.get("sentence", "")
        next_sent = data.get("next_sentence", "")
        photo_pair = data.get("photo_pair", [])  # 原始照片对
        subject_pair = data.get("subject_pair", [])  # 主体照片对

        # === 强制检查：必须有原始照片 ===
        if not photo_pair:
            return jsonify({"error": "必须提供原始照片（photo_pair），系统不支持纯文本生成模式。"}), 400

        # === 定义半结构化固定要求（将在AI生成结果后强制追加） ===
        HALF_STRUCTURED_RULES = """
【必须遵守的生成规则】：
1.  **场景过渡平滑性**：严禁场景/背景的突然切换、溶解、跳切或淡入淡出。所有背景变化必须通过主体人物转场实现，背景转场自然，必须与主体动作节奏同步，实现渐进、连贯的视觉演变。
2.  **主体动作自然度**：人物的所有动作、表情必须自然流畅，符合真实物理规律和人体工学，严禁浮夸、机械或扭曲的表现，以避免恐怖谷效应。
3.  **主体连贯性 (仅限过渡视频)**：视频叙事必须围绕核心主体（由参考图锁定）的自然演变展开，严禁主体在过渡中身份突变、替换或消失。
"""

        # === 处理主体照片 ===
        print(f"[主体照片检查] 收到 {len(subject_pair)} 张主体照片")
        has_valid_subject_photos = False
        valid_subject_paths = []

        for i, subject_url in enumerate(subject_pair):
            if subject_url:
                print(f"  - 主体照片 {i+1}: {subject_url[:100]}...")
                if subject_url.startswith("data:image"):
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
                    local_path = _resolve_local_path(subject_url)
                    if local_path and local_path.exists():
                        valid_subject_paths.append(str(local_path))
                        has_valid_subject_photos = True
                        print(f"    ✅ 找到有效主体照片: {local_path.name}")
                    else:
                        print(f"    ⚠️ 主体照片路径无效: {subject_url}")

        print(f"[主体照片检查结果] 有效主体照片: {len(valid_subject_paths)} 张")
        # 如果没有有效主体照片，将使用原始照片作为后续回退，但不在此处处理，逻辑下移。

        # === 处理原始照片 ===
        temp_images = []
        for i, photo_url in enumerate(photo_pair):
            local_path = _resolve_local_path(photo_url)
            if local_path and local_path.exists():
                temp_images.append(str(local_path))
                print(f"  ✅ 原始照片 {i+1}: 使用本地文件 {local_path.name}")
            else:
                # 下载远程图片
                fname = f"temp_{p_type}_{i}_{uuid.uuid4().hex}.jpg"
                temp_path = GENERATED_DIR / fname
                if photo_url.startswith('http'):
                    try:
                        with requests.get(photo_url, stream=True, timeout=30) as r:
                            r.raise_for_status()
                            with open(temp_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        temp_images.append(str(temp_path))
                        print(f"  ✅ 原始照片 {i+1}: 下载远程图片至 {fname}")
                    except Exception as e:
                        print(f"  ❌ 原始照片 {i+1} 下载失败: {e}")
                        return jsonify({"error": f"原始照片 {i+1} 下载失败: {e}"}), 400
                else:
                    print(f"  ❌ 原始照片 {i+1} 格式无法识别: {photo_url[:100]}...")
                    return jsonify({"error": f"原始照片 {i+1} 的 URL 格式无效。"}), 400

        if len(temp_images) == 0:
            return jsonify({"error": "无法获取任何有效的原始图片。"}), 400

        # === 构建用于分析的图片列表（原始+主体）===
        all_images_for_analysis = []
        # 决定最终使用的主体照片路径：优先用户提供的有效主体照，否则回退到原始照片。
        effective_subject_paths = []
        if has_valid_subject_photos and len(valid_subject_paths) >= len(temp_images):
            effective_subject_paths = valid_subject_paths[:len(temp_images)]
        else:
            print(f"⚠️ 主体照片不足或无效，将使用原始照片作为主体参考。")
            effective_subject_paths = temp_images  # 回退到原始照片

        # === 构建 custom_prompt (移除了末尾的半结构化规则) ===
        if p_type == "static":
            # 静态视频：第一张原始照片 + 第一张（有效）主体照片
            all_images_for_analysis = [temp_images[0], effective_subject_paths[0]]
            # 【修改点】custom_prompt 不再包含 HALF_STRUCTURED_RULES
            custom_prompt = f"""
【视频时长】5秒
【照片关系】照片2是照片1主体的面部特写，用于身份锁定

你是一名专业视频动效设计师。基于场景图（照片1）和面部特征（照片2），设计5秒静态转动态视频指令。

照片描述：{sentence}

【核心要求】：
1. **主体锁定**：通过照片2面部特征，在照片1中精准识别核心人物，所有动态围绕该主体展开

2. **5秒节奏**：
- 0-0.5秒：细微预备动作
- 0.5-4秒：核心动作展开（符合人物气质）
- 4-5秒：动作收尾与稳定定格

3. 【以下要求原话保留】
- 禁止人物替换或突变，5秒内主体身份必须绝对一致
- **动作表情必须自然符合物理规律** 
- 禁止突兀跳切、瞬间变化，所有动态必须渐进式

4. **输出**：描述5秒内主体的视觉变化过程（含时间节点），≤300字。
"""
        else:
            # 过渡视频：需要至少两张原始照片和对应的主体照
            if len(temp_images) < 2:
                return jsonify({"error": "过渡视频（type='transition'）需要至少提供2张原始照片（photo_pair）。"}), 400
            # 图片顺序：原图1，主体1，原图2，主体2
            all_images_for_analysis = [
                temp_images[0],
                effective_subject_paths[0],
                temp_images[1],
                effective_subject_paths[1] if len(effective_subject_paths) > 1 else effective_subject_paths[0]
            ]
            # 【修改点】custom_prompt 不再包含 HALF_STRUCTURED_RULES
            custom_prompt = f"""
【主体照片说明】：
- 照片2 = 第一张照片（照片1）中主体的面部特写
- 照片4 = 第二张照片（照片3）中主体的面部特写

你是一名专业的视频过渡效果设计师。请基于两张完整场景（照片1、3）和对应的面部特写（照片2、4），设计一段5秒时长的主体连贯过渡效果。

【核心要求 - 主体连贯性（最重要）】：
1. **主体身份锁定**：照片2和照片4所在的人物为各自照片的主体。然后你需要识别照片2和照片4在各自图片1和图片3中对应的位置，身体形态，穿着等重要元素，并在生成视频指令描述中我也要提到这个主体的面部、衣服、身体形态等特征，谁是主体由谁转换到谁。
2. **强制主体过渡**：视频必须清晰展现"照片2的主体"自然转化为"照片4的主体"，这是视频的核心叙事线索
3. **禁止主体突变**：严禁出现主体人物突然切换、替换或消失的情况，主体必须在5秒内保持视觉连续性

【5秒过渡节奏设计】：
- 0-1秒：首帧稳定，主体开始细微动作
- 1-4秒：**核心过渡阶段**，主体姿态/表情/角度从照片2状态向照片4状态自然演变，背景同步渐变。注意设计不得背景突然变换，强调主体动作和背景平滑过渡
- 4-5秒：过渡完成，主体定格为照片4状态，与尾帧无缝衔接

【禁止事项】：
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

        # === 调用 analyze_images 生成初步指令 ===
        print(f"[调用分析] 发送 {len(all_images_for_analysis)} 张图片进行分析...")
        ai_generated_prompt = analyze_images(all_images_for_analysis, custom_prompt)

        # === 【核心修正】在AI生成的结果后，强制追加半结构化规则 ===
        if ai_generated_prompt:
            # 移除AI生成结果可能自带的尾部换行和空格，然后追加固定规则
            final_prompt = ai_generated_prompt.strip() + "\n\n" + HALF_STRUCTURED_RULES.strip()
        else:
            final_prompt = HALF_STRUCTURED_RULES.strip()  # 如果AI生成失败，至少返回规则

        # === 清理临时生成的文件 ===
        for img_path in temp_images:
            if img_path.startswith(str(GENERATED_DIR)) and 'temp_' in img_path:
                try:
                    os.unlink(img_path)
                except:
                    pass
        for img_path in valid_subject_paths:  # 清理从base64保存的主体照
            if img_path.startswith(str(GENERATED_DIR)) and 'subject_' in img_path:
                try:
                    os.unlink(img_path)
                except:
                    pass

        if final_prompt:
            return jsonify({
                "prompt": final_prompt,  # 返回合并后的最终指令
                "subject_photos_status": {
                    "has_valid_subject_photos": has_valid_subject_photos,
                    "subject_count": len(valid_subject_paths),
                    "message": "主体照片已成功处理并用于生成" if has_valid_subject_photos else "使用原始照片作为主体参考"
                }
            })
        else:
            return jsonify({"error": "图像分析服务未能返回有效指令。"}), 500

    except Exception as e:
        print("refine-prompt error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/video-status/<task_id>', methods=['GET'])
def video_status(task_id):
    task = video_tasks.get(task_id)
    if not task: return jsonify({"error": "not found"}), 404
    return jsonify(task)


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

                    # 【修改点4】确保头像至少 300x300（可灵 API 要求像素不能太小）
                    min_avatar_size = 300
                    if face_img.shape[0] < min_avatar_size or face_img.shape[1] < min_avatar_size:
                        scale = min_avatar_size / min(face_img.shape[0], face_img.shape[1])
                        face_img = cv2.resize(
                            face_img,
                            (int(face_img.shape[1] * scale), int(face_img.shape[0] * scale)),
                            interpolation=cv2.INTER_LANCZOS4
                        )
                        print(f"    📐 头像 upscale 到 {face_img.shape[1]}x{face_img.shape[0]}")
                        
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
        n_pairs = len(local_paths) // 2
        print(f"[video task {task_id}] 共 {len(local_paths)} 张照片，{len(prompts)} 个prompt，将生成 {n_pairs} 段视频")
        for i in range(n_pairs):
            first = os.path.basename(local_paths[i * 2])
            tail  = os.path.basename(local_paths[i * 2 + 1])
            print(f"  片段 {i+1}/{n_pairs}: 首帧={first}  尾帧={tail}")

        # generate.py 固定输出到 static/video/generated_video.mp4
        video_output_dir = Path(__file__).parent / "static" / "video"
        video_output_dir.mkdir(parents=True, exist_ok=True)
        generated_video_path = video_output_dir / "generated_video.mp4"

        # 调用命令行生成
        cmd = ["python", "generate.py", "--photos", *local_paths, "--prompts", *[str(p) for p in prompts]]
        subprocess.run(cmd, check=True, cwd=os.path.dirname(__file__))

        # 将生成好的视频复制到 static/generated 并使用唯一文件名
        out_name = f"final_{uuid.uuid4().hex}.mp4"
        out_path = GENERATED_DIR / out_name
        if generated_video_path.exists():
            shutil.copy2(generated_video_path, out_path)
            video_url = f"{BACKEND_BASE}/static/generated/{out_name}"
        else:
            raise FileNotFoundError(f"generate.py 未输出视频文件: {generated_video_path}")

        video_tasks[task_id].update({"status": "success", "videoUrl": video_url})

    except Exception as e:
        print(f"Video task {task_id} failed: {e}")
        video_tasks[task_id].update({"status": "failed", "error": str(e)})
    finally:
        if temp_dir and temp_dir.exists(): shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)