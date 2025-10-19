import os
import base64
from openai import OpenAI

API_KEY = "sk-fbdc82229399417892a94c001b5ea873" # 替换成自己的key
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

class QwenChat:
    def __init__(self, api_key=API_KEY, base_url=BASE_URL):
        self.client = OpenAI(
            api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
            base_url=base_url
        )
        self.messages = []  # 存储完整的对话历史
        
    def _has_system_message(self):
        """检查消息历史中是否已存在 system 角色的消息"""
        return any(msg["role"] == "system" for msg in self.messages)

    def _is_valid_image_format(self, path):
        """检查文件扩展名是否为支持的图像格式"""
        if path.startswith("http://") or path.startswith("https://"):
            return True  # URL 不做格式限制
        supported_exts = {'.png', '.jpg', '.jpe', '.jpeg', '.tif', '.tiff', '.webp', '.bmp', '.heic'}
        ext = os.path.splitext(path.lower())[1]
        return ext in supported_exts

    def _url_or_base64(self, value):
        # 如果是 base64 图片字符串，直接返回
        if value.startswith("data:image"):
            return value
        # 如果是网络图片（URL）
        elif value.startswith("http://") or value.startswith("https://"):
            return value
        else:
            # 否则尝试读取本地路径
            with open(value, "rb") as img_file:
                data = img_file.read()
                return f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
            
    def get_response(
        self,
        prompt=None,
        system_prompt=None,
        image_path_list=[],
        model="qwen-plus",
        max_tokens=4096,
        temperature=0.5,
        enable_thinking=False,
        stream=False,
        enable_history=False,
        enable_image_input=False
    ):
        """
        获取Qwen模型的响应，支持单轮和多轮对话
        :param prompt: 用户输入的提示词
        :param system_prompt: 系统提示词（仅在第一次添加）
        :param image_path_list: 图像文件路径列表（支持本地路径或URL）
        :param model: 模型名称（模型参数列表：https://help.aliyun.com/zh/model-studio/getting-started/models）
        :param max_tokens: 最大生成token数
        :param temperature: 模型温度（温度越高，生成的文本更多样，反之，生成的文本更确定。取值范围：[0, 2)）
        :param enable_thinking: 是否启用思考过程
        :param stream: 是否启用流式输出
        :param enable_history: 是否使用并维护对话历史；False则仅本次对话有效
        :param enable_image_input: 是否启用图像输入（支持URL或Base64格式）
        :return: 模型响应内容
        """
        # if not enable_history:
        #     # 不启用历史：临时消息列表，只包含 system + 当前 prompt
        #     messages_list = []
        #     if system_prompt:
        #         messages_list.append({"role": "system", "content": system_prompt})
        #     if prompt:
        #         messages_list.append({"role": "user", "content": prompt})
        # else:
        #     # 启用历史：使用实例级 self.messages 维护上下文
        #     if system_prompt and len(self.messages) == 0:  # 只在第一次加入 system
        #         self.messages.append({"role": "system", "content": system_prompt})
        #     if prompt:
        #         self.messages.append({"role": "user", "content": prompt})
        #     messages_list = self.messages
                # 构建 content 列表（多模态）
        user_content = []

        # 添加图像（如果启用）
        if enable_image_input and image_path_list:
            for image_path in image_path_list:
                image_data_url = self._url_or_base64(image_path)
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": image_data_url}
                })

        # 添加文本
        if prompt:
            user_content.append({
                "type": "text",
                "text": prompt
            })

        # 构建消息列表
        if not enable_history:
            # 单轮模式：临时消息
            messages_list = []
            if system_prompt:
                if enable_image_input:
                    messages_list.append({
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}]
                    })
                else:
                    messages_list.append({"role": "system", "content": system_prompt})
            if user_content:
                messages_list.append({"role": "user", "content": user_content})
        else:
            # 多轮模式：使用历史
            if system_prompt and not self._has_system_message():
                if enable_image_input:
                    self.messages.append({
                        "role": "system",
                        "content": [{"type": "text", "text": system_prompt}]
                    })
                else:
                    self.messages.append({"role": "system", "content": system_prompt})

            if user_content:
                self.messages.append({"role": "user", "content": user_content})
            messages_list = self.messages

        # 调用模型
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages_list,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
                extra_body={"enable_thinking": enable_thinking},
            )
            response = completion.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Model call failed: {str(e)}")
        
        if response and enable_history:
            if user_content:
                self.messages.append({"role": "assistant", "content": [{"type": "text", "text": response}]})
            else:
                self.messages.append({"role": "assistant", "content": response})

        return response if response else "No response received."

    def clear_history(self):
        """清空对话历史"""
        self.messages.clear()

    def get_history(self):
        """获取当前对话历史"""
        return self.messages.copy()