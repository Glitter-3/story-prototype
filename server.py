from flask import Flask, request, jsonify
from qwen import QwenChat
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)  # 允许跨域请求

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
    

# @app.route('/generate-prompts', methods=['POST'])
# def generate_prompts():
#     try:
#         data = request.get_json()
#         photos = data['photos']
#         narratives = data['narratives']

#         # Step 1: 调用Qwen进行分句和生成prompt
#         system_prompt = f"""你是一个叙事视觉设计助手。
#             请把用户给出的叙述文本合理分句，每句能代表一个独立的视觉场景。
#             对于每一句话，生成一个适合文生图的中文prompt（20字左右，描述画面内容）。
#             请以JSON数组返回，每个元素包含 "sentence" 和 "prompt"。
#             """       
#         prompt = f"""
#             用户提供的叙述文本内容如下：
#             {narratives}
#             请结合上述内容生成符合 system_prompt 要求的 JSON 数组。
#             """
#         response = qwen.get_response(
#             prompt=prompt,
#             system_prompt=system_prompt,
#             image_path_list=photos,
#             model="qwen-vl-max",
#             enable_image_input=True
#         )
#         print('生成的文本对：', response)
#         result = response.json()

#         # 提取Qwen输出文本（按实际返回格式调整）
#         text_output = result["output"]["text"] if "output" in result else result.get("result", "")
#         # 尝试解析为JSON数组
#         try:
#             import json
#             qwen_sentences = json.loads(text_output)
#         except Exception:
#             qwen_sentences = [{"sentence": narratives, "prompt": "no prompt"}]

#         # Step 2: 匹配照片
#         sentence_pairs = []
#         for i, item in enumerate(qwen_sentences):
#             photo = photos[i] if i < len(photos) else None
#             sentence_pairs.append({
#                 "sentence": item["sentence"],
#                 "photo": photo,
#                 "prompt": item["prompt"] if photo is None else None
#             })

#         return jsonify({"sentence_pairs": sentence_pairs})

    
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/generate-prompts', methods=['POST'])
def generate_prompts():
    try:
        data = request.get_json()

        photos = data['photos']  # 图片路径列表
        print("📩 收到的 图片 数据：", photos)
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
            qwen_sentences = json.loads(text_output)
        except Exception as e:
            print("⚠️ JSON 解析失败:", e, text_output)
            qwen_sentences = [{"sentence": narratives, "prompt": "no prompt"}]
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
                scores = json.loads(str(match_response))
            except:
                scores = []

            # 找出最高分的句子
            if scores:
                best_match = max(scores, key=lambda x: x.get("score", 0))
                best_idx = best_match.get("index", 0) - 1  # 转成从0开始的索引
                best_score = best_match.get("score", 0)
            else:
                best_idx, best_score = None, 0

            if best_score > 60 and best_idx is not None and best_idx not in matched_indices:
                matched_indices.add(best_idx)
                sentence_pairs.append({
                    "photo": photo,
                    "sentence": qwen_sentences[best_idx]["sentence"],
                    "prompt": None
                })
            else:
                sentence_pairs.append({
                    "photo": photo,
                    "sentence": None,
                    "prompt": None
                })

        # Step 3: 把剩余未匹配的句子添加为需生成图的 prompt
        for idx, item in enumerate(qwen_sentences):
            if idx not in matched_indices:
                sentence_pairs.append({
                    "photo": None,
                    "sentence": item["sentence"],
                    "prompt": item["prompt"]
                })

        return jsonify({"sentence_pairs": sentence_pairs})

        # # Step 2: 对每张照片寻找语义最接近的句子（photo→sentence）
        # matched_indices = set()  # 记录已被匹配的句子索引
        # sentence_pairs = []

        # for photo_idx, photo in enumerate(photos):
        #     best_match = {"index": None, "score": 0}

        #     for idx, item in enumerate(qwen_sentences):
        #         if idx in matched_indices:
        #             continue

        #         sentence = item["sentence"]
        #         match_prompt = f"""
        #         你是一个图像语义理解助手。
        #         用户提供了一张图片和一句文字描述。
        #         请你判断这张图片与文字的语义相关程度（0~100分）。
        #         输出格式严格为：{{"score": 数值}}
        #         叙述内容："{sentence}"
        #         """

        #         match_response = qwen.get_response(
        #             prompt=match_prompt,
        #             system_prompt="仅根据语义相关性输出一个数值评分。",
        #             image_path_list=[photo],
        #             model="qwen-vl-max",
        #             enable_image_input=True
        #         )

        #         try:
        #             score = json.loads(str(match_response)).get("score", 0)
        #         except:
        #             score = 0

        #         if score > best_match["score"]:
        #             best_match = {"index": idx, "score": score}

        #     # 如果最高分超过阈值，则该图片与该句匹配
        #     if best_match["score"] > 60 and best_match["index"] is not None:
        #         matched_idx = best_match["index"]
        #         matched_indices.add(matched_idx)
        #         sentence_pairs.append({
        #             "photo": photo,
        #             "sentence": qwen_sentences[matched_idx]["sentence"],
        #             "prompt": None
        #         })
        #     else:
        #         # 没有找到合适的句子
        #         sentence_pairs.append({
        #             "photo": photo,
        #             "sentence": None,
        #             "prompt": None
        #         })

        # # Step 3: 把剩余未匹配的句子作为“需生成图”的 prompt
        # for idx, item in enumerate(qwen_sentences):
        #     if idx not in matched_indices:
        #         sentence_pairs.append({
        #             "photo": None,
        #             "sentence": item["sentence"],
        #             "prompt": item["prompt"]
        #         })

        # return jsonify({"sentence_pairs": sentence_pairs})

    except Exception as e:
        return jsonify({"error": str(e)}), 500




if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

