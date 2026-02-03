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
                sentence_pairs.append({
                    "index": idx,
                    "photo": None,
                    "sentence": item["sentence"],
                    "prompt": item["prompt"],
                    "group_index": gIdx,
                    "subgroup_index": sgIdx
                })
        # ===== 新增结束 =====

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

            # 最多取 4 张
            proc_photos = photo_list[:4]

            try:
                generated_urls = []

                # 构造 subject_image_list（1–4 张都合法）
                subject_imgs = [
                    {"subject_image": extract_base64(img)}
                    for img in proc_photos
                ]

                # 不用 style_image 

                task_result = multi_ig.run(
                    subject_imgs=subject_imgs,
                    headers=HEADERS,
                    prompt=prompt,
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
                4. 指令需详细具体，紧扣照片元素，可直接作为AI视频生成工具的输入。注意一定要强调有动作不能只是镜头的放大所辖
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
                5. 指令紧扣两张照片元素，可直接作为AI视频生成工具的输入，内容详实、逻辑清晰。注意一定要强调不能画面突然转化，必须要用主体平滑的过渡背景过去。
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