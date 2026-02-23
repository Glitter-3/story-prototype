import requests
import base64
import time
import json
import jwt
import re

# ================== 配置区 ==================
ACCESS_KEY= "ALPHa9RkmN8gDbmQLbkYBfHBJRAhhtmm"
SECRET_KEY= "PNhKAyntFDJGEgYrmL4Hd8KCDE4yRHeY"
API_BASE_URL = "https://api-beijing.klingai.com"  # API域名


class ImageGenerator:
    """
    文生图和单图参考生图任务管理类
    支持创建任务、轮询结果、查询任务列表等功能
    """

    def __init__(self, access_key=ACCESS_KEY, secret_key=SECRET_KEY, api_base_url=API_BASE_URL):
        self.access_key = access_key
        self.secret_key = secret_key
        self.api_base_url = api_base_url

    # ================== 工具方法 ==================
    def _encode_jwt_token(self, exp_time=7200):
        """生成JWT Token"""
        headers = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.access_key,
            "exp": int(time.time()) + exp_time,
            "nbf": int(time.time()) - 5
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)

    def _url_or_base64(self, value):
        """将本地图片转为Base64，URL则保留原样"""
        if value.startswith("http://") or value.startswith("https://"):
            return value
        else:
            try:
                with open(value, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode('utf-8')
            except Exception as e:
                raise FileNotFoundError(f"无法读取图片文件: {value}, 错误: {e}")

    # ================== 核心方法 ==================
    def create_task(
        self,
        image_path=None,
        prompt="",
        model_name="kling-v2",
        n=1,
        aspect_ratio="3:4",
        callback_url=None,
        headers=None
    ):
        """
        创建文生图和单图参考生图任务
        :param subject_imgs: list of dict, [{"subject_image": "path_or_url"}]
        :param imge_path: 本地图片路径或URL
        :param prompt: 提示词
        :param model_name: 模型名称
        :param n: 生成数量
        :param aspect_ratio: 宽高比
        :param callback_url: 回调地址
        :param headers: 请求头（需包含Authorization）
        :return: 响应数据 dict 或 None
        """
        if not headers:
            raise ValueError("headers 不能为空，请提供包含 Authorization 的请求头")

        payload = {
            "model_name": model_name,
            "prompt": prompt,
            "n": n,
            "aspect_ratio": aspect_ratio
        }
        if image_path:
            payload["image"] = self._url_or_base64(image_path)

        if callback_url:
            payload["callback_url"] = callback_url

        url = f"{self.api_base_url}/v1/images/generations"
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                task_id = result["data"]["task_id"]
                print(f"✅ 任务创建成功！任务ID: {task_id}")
                return result
            else:
                print(f"❌ 任务创建失败: {result.get('message', '未知错误')}")
                return result
        else:
            print(f"❌ HTTP Error: {response.status_code}, {response.text}")
            return None

    def get_task_result(self, task_id, headers):
        """
        查询单个任务结果
        :param task_id: 任务ID
        :param headers: 请求头
        :return: 响应数据 dict 或 None
        """
        url = f"{self.api_base_url}/v1/images/generations/{task_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                status = result["data"]["task_status"]
                print(f"📌 任务ID: {task_id} | 状态: {status}")
                if status == "succeed":
                    images = result["data"]["task_result"]["images"]
                    for img in images:
                        print(f"🖼️  生成图片 {img['index']}: {img['url']}")
                elif status == "failed":
                    msg = result["data"].get("task_status_msg", "未知原因")
                    print(f"❌ 任务失败: {msg}")
                return result
            else:
                print(f"❌ 查询失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}, {response.text}")
        return None

    def list_tasks(self, headers, pageNum=1, pageSize=10):
        """
        查询任务列表
        :param headers: 请求头
        :param pageNum: 页码
        :param pageSize: 每页数量
        :return: 响应数据 dict 或 None
        """
        url = f"{self.api_base_url}/v1/images/generations"
        params = {"pageNum": pageNum, "pageSize": pageSize}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                tasks = result["data"]
                print(f"📋 共查询到 {len(tasks)} 个任务:")
                for task in tasks:
                    print(f"  🔹 {task['task_id']} | 状态: {task['task_status']} | 创建时间: {task['created_at']}")
                return result
            else:
                print(f"❌ 查询失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}, {response.text}")
        return None

    def run(
        self,
        headers,
        prompt="",
        image_path="",
        model_name="kling-v2",
        n=1,
        aspect_ratio="16:9",
        callback_url=None,
        max_wait=300,
        interval=10
    ):
        """
        主运行方法：创建任务并轮询结果
        :return: 最终任务结果 dict
        """
        # Step 1: 创建任务
        task_result = self.create_task(
            image_path=image_path,
            prompt=prompt,
            model_name=model_name,
            n=n,
            aspect_ratio=aspect_ratio,
            callback_url=callback_url,
            headers=headers
        )
        if not task_result:
            raise RuntimeError("任务创建失败，无法继续")

        task_id = task_result["data"]["task_id"]

        # Step 2: 轮询任务状态
        for _ in range(max_wait // interval):
            time.sleep(interval)
            result = self.get_task_result(task_id, headers)
            if not result:
                continue
            status = result["data"]["task_status"]
            if status in ["succeed", "failed"]:
                return result

        # 超时仍未完成
        print(f"⏰ 任务 {task_id} 在 {max_wait} 秒内未完成，已超时")
        return self.get_task_result(task_id, headers)  # 返回最后一次查询结果
    


class MultiImage2Image:
    """
    多图参考生图任务管理类
    支持创建任务、轮询结果、查询任务列表等功能
    """

    def __init__(self, access_key=ACCESS_KEY, secret_key=SECRET_KEY, api_base_url=API_BASE_URL):
        self.access_key = access_key
        self.secret_key = secret_key
        self.api_base_url = api_base_url

    # ================== 工具方法 ==================

    def _encode_jwt_token(self, exp_time=7200):
        """生成JWT Token"""
        headers = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.access_key,
            "exp": int(time.time()) + exp_time,
            "nbf": int(time.time()) - 5
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)

    # def _url_or_base64(self, value):
    #     """将本地图片转为Base64，URL则保留原样"""
    #     if value.startswith("http://") or value.startswith("https://"):
    #         return value
    #     else:
    #         try:
    #             with open(value, "rb") as image_file:
    #                 return base64.b64encode(image_file.read()).decode('utf-8')
    #         except Exception as e:
    #             raise FileNotFoundError(f"无法读取图片文件: {value}, 错误: {e}")

    def _url_or_base64(self, value):
        """将本地图片转为Base64，URL则保留原样；若已是纯base64字符串（无data:前缀），也原样返回"""
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}: {value}")

        # ✅ 情况1：URL → 直接返回
        if value.startswith(("http://", "https://")):
            return value

        # ✅ 情况2：纯 base64 字符串（无 data: 前缀）
        # 合法 base64 字符集：字母数字 + '+' '/'，结尾可有 '=' 填充，长度 ≡ 0 mod 4（宽松判断）
        # 注意：可灵要求 *不能* 有 "data:image/..." 前缀！
        if re.fullmatch(r'[A-Za-z0-9+/]*={0,2}', value) and len(value) > 100:
            # 粗略判断：长度 >100 + 符合 base64 字符集 → 很可能是 base64
            try:
                # 可选：做一次解码验证（开销小，防误判）
                base64.b64decode(value, validate=True)
                return value  # 验证通过，原样返回
            except Exception:
                pass  # 验证失败，继续走文件路径逻辑

        # ✅ 情况3：本地文件路径 → 读取并转 base64
        try:
            with open(value, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise FileNotFoundError(f"无法读取图片文件或非法 base64: {value[:100]}..., 错误: {e}")

    # ================== 核心方法 ==================

    def create_task(
        self,
        subject_imgs=[],
        prompt="",
        scence_img=None,
        style_img=None,
        model_name="kling-v2",
        n=1,
        aspect_ratio="16:9",
        callback_url=None,
        external_task_id=None,
        headers=None
    ):
        """
        创建多图参考生图任务
        :param subject_imgs: list of dict, 如 [{"subject_image": "path_or_url"}]
        :param prompt: 提示词
        :param scence_img: 场景图路径或URL
        :param style_img: 风格图路径或URL
        :param model_name: 模型名称
        :param n: 生成数量
        :param aspect_ratio: 宽高比
        :param callback_url: 回调地址
        :param external_task_id: 自定义任务ID
        :param headers: 请求头（需包含Authorization）
        :return: 响应数据 dict 或 None
        """
        if not headers:
            raise ValueError("headers 不能为空，请提供包含 Authorization 的请求头")

        if len(subject_imgs) < 1 or len(subject_imgs) > 4:
            raise ValueError("subject_imgs 必须包含 1 到 4 张图片")

        # 处理主体图片
        subject_image_list = [
            {key: self._url_or_base64(value) for key, value in item.items()}
            for item in subject_imgs
        ]

        payload = {
            "model_name": model_name,
            "prompt": prompt,
            "subject_image_list": subject_image_list,
            "n": n,
            "aspect_ratio": aspect_ratio
        }

        if scence_img:
            payload["scence_image"] = self._url_or_base64(scence_img)
        if style_img:
            payload["style_image"] = self._url_or_base64(style_img)
        if callback_url:
            payload["callback_url"] = callback_url
        if external_task_id:
            payload["external_task_id"] = external_task_id

        url = f"{self.api_base_url}/v1/images/multi-image2image"
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                task_id = result["data"]["task_id"]
                print(f"✅ 任务创建成功！任务ID: {task_id}")
                return result
            else:
                print(f"❌ 任务创建失败: {result.get('message', '未知错误')}")
                return result
        else:
            print(f"❌ HTTP Error: {response.status_code}, {response.text}")
            return None

    def get_task_result(self, task_id, headers):
        """
        查询单个任务结果
        :param task_id: 任务ID
        :param headers: 请求头
        :return: 响应数据 dict 或 None
        """
        url = f"{self.api_base_url}/v1/images/multi-image2image/{task_id}"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                status = result["data"]["task_status"]
                print(f"📌 任务ID: {task_id} | 状态: {status}")
                if status == "succeed":
                    images = result["data"]["task_result"]["images"]
                    for img in images:
                        print(f"🖼️  生成图片 {img['index']}: {img['url']}")
                elif status == "failed":
                    msg = result["data"].get("task_status_msg", "未知原因")
                    print(f"❌ 任务失败: {msg}")
                return result
            else:
                print(f"❌ 查询失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}, {response.text}")
        return None

    def list_tasks(self, headers, pageNum=1, pageSize=10):
        """
        查询任务列表
        :param headers: 请求头
        :param pageNum: 页码
        :param pageSize: 每页数量
        :return: 响应数据 dict 或 None
        """
        url = f"{self.api_base_url}/v1/images/multi-image2image"
        params = {"pageNum": pageNum, "pageSize": pageSize}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                tasks = result["data"]
                print(f"📋 共查询到 {len(tasks)} 个任务:")
                for task in tasks:
                    print(f"  🔹 {task['task_id']} | 状态: {task['task_status']} | 创建时间: {task['created_at']}")
                return result
            else:
                print(f"❌ 查询失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}, {response.text}")
        return None

    def run(
        self,
        subject_imgs,
        headers,
        prompt="",
        scence_img=None,
        style_img=None,
        model_name="kling-v2",
        n=1,
        aspect_ratio="3:4",
        callback_url=None,
        external_task_id=None,
        max_wait=300,
        interval=10
    ):
        """
        主运行方法：创建任务并轮询结果
        :return: 最终任务结果 dict
        """
        # Step 1: 创建任务
        task_result = self.create_task(
            subject_imgs=subject_imgs,
            prompt=prompt,
            scence_img=scence_img,
            style_img=style_img,
            model_name=model_name,
            n=n,
            aspect_ratio=aspect_ratio,
            callback_url=callback_url,
            external_task_id=external_task_id,
            headers=headers
        )
        if not task_result:
            raise RuntimeError("任务创建失败，无法继续")

        task_id = task_result["data"]["task_id"]

        # Step 2: 轮询任务状态
        for _ in range(max_wait // interval):
            time.sleep(interval)
            result = self.get_task_result(task_id, headers)
            if not result:
                continue
            status = result["data"]["task_status"]
            if status in ["succeed", "failed"]:
                return result

        # 超时仍未完成
        print(f"⏰ 任务 {task_id} 在 {max_wait} 秒内未完成，已超时")
        return self.get_task_result(task_id, headers)  # 返回最后一次查询结果