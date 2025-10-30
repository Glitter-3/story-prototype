import os
import re
import json
import uuid
import time
import base64
import requests
from pathlib import Path
from kling import ImageGenerator
from datetime import datetime
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
        base = str(int(time.time()))  # 使用时间戳作为文件名
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


# 修改后的 download_to_generated：下载远程 URL 到 static/generated，并用时间戳+uuid命名保存
def download_to_generated(url, filename=None):
    try:
        import requests
        # 如果用户没有提供 filename，则从 url 解析出一个基本名字并清理
        if not filename:
            filename = sanitize_filename_from_url(url)
        # 为文件名加上时间戳和 uuid 前缀，保留原扩展名
        ext = os.path.splitext(filename)[1] or ".jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_base = uuid.uuid4().hex
        final_name = f"{timestamp}_{safe_base}{ext}"
        out_path = GENERATED_DIR / final_name

        # 使用 stream=True 分块写入，避免大文件一次性占内存
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        # 返回可供前端直接访问的绝对 URL
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
            if not prompt:
                # 跳过没有 prompt 的项（front-end 不需要生成）
                results.append({"index": idx, "prompt": None, "generated_urls": [], "note": "no prompt"})
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
                results.append({"index": idx, "prompt": prompt, "generated_urls": [], "error": str(e)})
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
                                # 当前时间戳
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                # 文件名示例：20251030_113845_5a7b3c9b2f6d4e3a.jpg
                                fn = f"{timestamp}_{uuid.uuid4().hex}.jpg"
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

            results.append({"index": idx, "prompt": prompt, "generated_urls": generated_urls})
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
            questions = json.loads(result)
        except json.JSONDecodeError:
            questions = []  # 避免报错
            print("⚠️ JSON 解析失败:", result)

        return jsonify({"questions": questions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/generate-prompts', methods=['POST'])
def generate_prompts():
    try:
        data = request.get_json()

        photos = data['photos']  # 图片路径列表
        narratives = data['narrative']  # 用户输入叙述文本

        # Step 1：调用 Qwen 分句+生成 prompt
        system_prompt_1 = """
        你是一个叙事视觉设计助手。
        请把用户给出的叙述文本合理分句，每句代表一个独立的视觉场景。
        对每一句生成一个适合文生图的中文prompt（约30字，描述画面内容）。 
        注意：中文prompt最重要的是主体、主体动作和场景，用自然语言描述即可，此外，可以增加风格、光影、色彩等美学要求的词语。
        主体:对主体外貌细节和姿态等的描述，可通过自然语言描述，如发型发色、服饰穿搭、五官形态、肢体姿态等；
        主体行为:对主体行为姿态的描述，不宜过于复杂，定格某一个画面的行为动作即可；
        场景:场景是主体所处的环境，包括前景、背景等;对主体所处环境的细节描述，如室内场景、室外场景、自然场景等。
        美学补充:风格、光影、色彩、镜头语言、氛围等美学要求。
        你需要分析叙述文本描述的具体时代和地区背景，在每一个prompt中强调时代和地域（一般是中国）。
        输出 JSON 数组格式： 
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

        if isinstance(response_1, dict) and "output" in response_1:
            text_output = response_1["output"].get("text", "")
        else:
            text_output = str(response_1)

        try:
            qwen_sentences = json.loads(text_output)
        except Exception as e:
            qwen_sentences = [{"sentence": narratives, "prompt": "no prompt"}]
        print("📝 Qwen 分句+prompt 结果：", qwen_sentences)

        # Step 2：对每张照片寻找语义最接近的句子（photo→sentence）
        matched_indices = set()
        sentence_pairs = []

        for photo_idx, photo in enumerate(photos):
            all_sentences_text = "\n".join(
                [f"{i+1}. {item['sentence']}" for i, item in enumerate(qwen_sentences)]
            )

            match_prompt = f"""
            你是一个图像语义匹配助手。
            下面有一张图片，以及若干文字描述（编号1~{len(qwen_sentences)}）。
            请你对每个文字描述与图片的语义相关性打分（0~100分）。
            输出 JSON 数组格式：[{{"index": 1, "score": 78}}, ...]
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
                scores = json.loads(str(match_response))
            except:
                scores = []

            if scores:
                best_match = max(scores, key=lambda x: x.get("score", 0))
                best_idx = best_match.get("index", 0) - 1
                best_score = best_match.get("score", 0)
            else:
                best_idx, best_score = None, 0

            if best_score > 60 and best_idx is not None and best_idx not in matched_indices:
                matched_indices.add(best_idx)
                sentence_pairs.append({
                    "photo": photo,
                    "sentence": qwen_sentences[best_idx]["sentence"],
                    "prompt": None,
                    "index": best_idx  # 增加 index 字段
                })
            else:
                sentence_pairs.append({
                    "photo": photo,
                    "sentence": None,
                    "prompt": None,
                    "index": None  # 无匹配则设置为 None
                })

        # Step 3：把剩余未匹配的句子添加为需生成图的 prompt
        for idx, item in enumerate(qwen_sentences):
            if idx not in matched_indices:
                sentence_pairs.append({
                    "photo": None,
                    "sentence": item["sentence"],
                    "prompt": item["prompt"],
                    "index": idx  # 增加 index 字段
                })

        # 按照 index 字段进行排序
        sentence_pairs.sort(key=lambda x: x.get('index', 0))

        return jsonify({"sentence_pairs": sentence_pairs})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/integrate-text', methods=['POST'])
def integrate_text():
    """
    接收：
    {
      "narrative": "...",          # Stage2 的口述（字符串，可能带 HTML）
      "qa_pairs": [{"question":"...", "answer":"..."} , ...],
      "options": {"output_format": "text"}  # 可选
    }
    返回：
    { "integrated_text": "......" }
    """
    try:
        data = request.get_json()
        narrative = data.get("narrative", "") or ""
        qa_pairs = data.get("qa_pairs", []) or []
        options = data.get("options", {})

        # 将 qa_pairs 转成可读格式（文本）
        qa_text_lines = []
        for i, qa in enumerate(qa_pairs):
            q = qa.get("question") or qa.get("text") or ""
            a = qa.get("answer") or ""
            qa_text_lines.append(f"{i+1}. 问：{q}\n   答：{a}")

        qa_text = "\n".join(qa_text_lines)
        print("📝 整合文本的 QA 内容：", qa_text)

        # system_prompt: 指导 qwen 如何输出
        system_prompt = """
        你是一名专业的叙事写作助手。任务是把下列用户的口述（可能是碎片或回忆）以及用户在与 AI 提问时给出的问答对整合成一段连贯、流畅、自然的中文叙述文本。
        要求：
        1) 以中文输出，控制在 2-6 段话内（若内容较少则一段即可），句子通顺，逻辑清晰。
        2) 保留事实性细节（时间、地点、人物、重要事件或情绪），但不得编造未提供的新事实；可以对语序与衔接做合理润色与合成。
        3) 若问答中包含具体细节（如名字/地点/关联时间），将其合理并入叙述；若存在矛盾信息，请以“根据记忆/描述”这种措辞处理。
        4) 输出纯文本（不要返回 JSON），不要添加额外的解释、元信息或注释。
        """

        # user prompt：把 narrative 与 qa_text 一起提供
        user_prompt = f"""
        用户的口述（原始）：
        {narrative}

        用户在回答 AI 提问时的问答记录（按序）如下：
        {qa_text}

        请你把上面两部分内容合成一段连贯的叙述。输出纯文本即可。
        """

        # 调用 qwen（保持你项目中 qwen.get_response 的用法）
        response = qwen.get_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            image_path_list=[],
            model="qwen-vl-max",
            enable_image_input=False
        )

        # response 可能是字符串或 dict，根据你现有 get_response 行为处理
        if isinstance(response, dict) and "output" in response:
            integrated = response["output"].get("text", "")
        else:
            integrated = str(response)

        # 做个简单清洗（移除过度的前后引号或多余空行）
        integrated = integrated.strip().strip('\"').strip()

        return jsonify({"integrated_text": integrated})
    except Exception as e:
        print("integrate-text 出错：", e)
        return jsonify({"error": str(e)}), 500




if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

