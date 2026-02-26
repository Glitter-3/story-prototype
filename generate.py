import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import argparse
import subprocess
import shutil
from urllib.parse import urljoin
from PIL import Image

<<<<<<< HEAD

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "static", "video")
OUTPUT_FILENAME = "generated_video.mp4"  
=======
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "static", "video")
OUTPUT_FILENAME = "generated_video.mp4"
>>>>>>> 48b5ea9 (submit by lue)
FFMPEG_CMD = "ffmpeg"
PROFILE_DIR = os.path.join(SCRIPT_DIR, "playwright_profile")


def check_and_adjust_image_size(image_paths):
<<<<<<< HEAD
    """检查所有图片尺寸是否与第一张图片一致"""
    if not image_paths:
        return image_paths
    
=======
    """
    检查所有图片尺寸是否与第一张图片一致，并将调整后的图片保存到临时目录。
    返回调整后的图片路径列表和临时目录路径。
    """
    if not image_paths:
        return image_paths, None

>>>>>>> 48b5ea9 (submit by lue)
    # 验证所有输入文件存在
    for path in image_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌❌ 输入文件不存在: {path}")
<<<<<<< HEAD
    
=======

>>>>>>> 48b5ea9 (submit by lue)
    try:
        with Image.open(image_paths[0]) as base_img:
            base_size = base_img.size
            print(f"📏📏 基准图片尺寸: {base_size[0]}x{base_size[1]}")
<<<<<<< HEAD
        
        adjusted_paths = []
        temp_dir = os.path.join(SCRIPT_DIR, "temp_adjusted_images")
        os.makedirs(temp_dir, exist_ok=True)
        
=======

        adjusted_paths = []
        temp_dir = os.path.join(SCRIPT_DIR, "temp_adjusted_images")
        os.makedirs(temp_dir, exist_ok=True)

>>>>>>> 48b5ea9 (submit by lue)
        for i, img_path in enumerate(image_paths):
            try:
                with Image.open(img_path) as img:
                    current_size = img.size
                    if current_size == base_size:
                        print(f"✅ 尺寸正确: {os.path.basename(img_path)}")
                        adjusted_paths.append(img_path)
                        continue
<<<<<<< HEAD
                    
                    print(f"🔄🔄 调整: {current_size} -> {base_size}")
                    resized_img = img.resize(base_size, Image.Resampling.LANCZOS)
                    temp_path = os.path.join(temp_dir, f"adjusted_{i}_{os.path.basename(img_path)}")
                    
=======

                    print(f"🔄🔄 调整: {current_size} -> {base_size}")
                    resized_img = img.resize(base_size, Image.Resampling.LANCZOS)
                    temp_path = os.path.join(temp_dir, f"adjusted_{i}_{os.path.basename(img_path)}")

>>>>>>> 48b5ea9 (submit by lue)
                    if img_path.lower().endswith(('.jpg', '.jpeg')):
                        resized_img.save(temp_path, 'JPEG', quality=95)
                    else:
                        resized_img.save(temp_path)
<<<<<<< HEAD
                    
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        adjusted_paths.append(temp_path)
                        print(f"✅ 保存: {temp_path}")
                    else:
                        print(f"⚠️ 写入失败，使用原图: {img_path}")
                        adjusted_paths.append(img_path)
                        
            except Exception as e:
                print(f"❌❌ 处理失败: {e}，使用原图: {img_path}")
                adjusted_paths.append(img_path)
        
        print(f"📁📁 临时文件保留在: {temp_dir}")
        return adjusted_paths
        
    except Exception as e:
        print(f"❌❌ 图片尺寸检查失败: {e}")
        return image_paths


async def get_all_video_srcs(page):
    """获取视频链接"""
=======

                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        adjusted_paths.append(temp_path)
                        print(f"✅ 保存调整后图片: {temp_path}")
                    else:
                        print(f"⚠️ 调整后图片写入失败，使用原图: {img_path}")
                        adjusted_paths.append(img_path)

            except Exception as e:
                print(f"❌❌ 图片处理失败: {e}，使用原图: {img_path}")
                adjusted_paths.append(img_path)

        print(f"📁📁 临时图片目录: {temp_dir}")
        return adjusted_paths, temp_dir

    except Exception as e:
        print(f"❌❌ 图片尺寸检查失败: {e}")
        return image_paths, None


async def get_all_video_srcs(page):
    """获取页面中所有视频元素的src属性值"""
>>>>>>> 48b5ea9 (submit by lue)
    try:
        videos = await page.query_selector_all("video[src]")
        srcs = []
        for v in videos:
            url = await v.get_attribute("src")
            if url and url not in srcs:
                srcs.append(url)
<<<<<<< HEAD
        print(f"🔍🔍 检测到 {len(srcs)} 个视频")
=======
        print(f"🔍🔍 检测到 {len(srcs)} 个视频元素")
>>>>>>> 48b5ea9 (submit by lue)
        return srcs
    except Exception as e:
        print(f"❌❌ 获取视频链接失败: {e}")
        return []


async def download_file(session, url, save_path):
<<<<<<< HEAD
    """下载视频 - 带验证"""
    try:
        if not url or not isinstance(url, str):
            raise ValueError(f"无效的URL: {url}")
        
        print(f"📥📥 下载: {url[:80]}...")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        dir_path = os.path.dirname(save_path)
        if not os.access(dir_path, os.W_OK):
            raise PermissionError(f"目录无写权限: {dir_path}")
        
        timeout = aiohttp.ClientTimeout(total=300)  
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            
            if resp.status != 200:
                raise Exception(f"HTTP错误: {resp.status}")
            
=======
    """下载指定URL的文件到本地路径"""
    try:
        if not url or not isinstance(url, str):
            raise ValueError(f"无效的URL: {url}")

        print(f"📥📥 下载: {url[:80]}...")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        dir_path = os.path.dirname(save_path)
        if not os.access(dir_path, os.W_OK):
            raise PermissionError(f"目录无写权限: {dir_path}")

        timeout = aiohttp.ClientTimeout(total=300)
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()

            if resp.status != 200:
                raise Exception(f"HTTP错误: {resp.status}")

>>>>>>> 48b5ea9 (submit by lue)
            with open(save_path, "wb") as f:
                downloaded = 0
                while True:
                    chunk = await resp.content.read(1024 * 64)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
<<<<<<< HEAD
                
                if downloaded == 0:
                    raise Exception("下载数据为空")
        
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"✅ 保存: {save_path} ({os.path.getsize(save_path)} bytes)")
        else:
            raise Exception(f"文件保存失败: {save_path}")
        
=======

                if downloaded == 0:
                    raise Exception("下载数据为空")

        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            print(f"✅ 文件保存成功: {save_path} ({os.path.getsize(save_path)} 字节)")
        else:
            raise Exception(f"文件保存失败: {save_path}")

>>>>>>> 48b5ea9 (submit by lue)
    except Exception as e:
        print(f"❌❌ 下载失败: {e}")
        raise


async def initial_setup(page):
<<<<<<< HEAD
    """首次登录即梦AI"""
=======
    """
    首次登录即梦AI，并设置视频生成模式和模型
    登录判断依据：检查是否存在按钮<div class="login-button-jDhuVc">登录</div>
    """
>>>>>>> 48b5ea9 (submit by lue)
    JIMENG_URL = "https://jimeng.jianying.com/ai-tool/home/"
    await page.goto(JIMENG_URL)
    await asyncio.sleep(2)

<<<<<<< HEAD
    login_btn = await page.query_selector("div.login-button-tP78Sd")
    if login_btn:
        try:
            await login_btn.click()
            await asyncio.sleep(1)
            agree_btn = await page.query_selector("button.agree-button-G3z4aB")
            if agree_btn:
                await agree_btn.click()
                print("💬💬 已点击同意按钮")
   
            await page.wait_for_selector("div.login-button-tP78Sd", state="detached", timeout=300000)
        except Exception as e:
            print("❌❌ 首次登录流程出错：", e)
            raise
    else:
        print("🔓🔓 已检测到登录状态，跳过登录")

    # 选择视频生成和时长
=======
    # 修改：使用新的登录按钮选择器
    login_btn = await page.query_selector("div.login-button-jDhuVc")
    if login_btn:
        login_text = await login_btn.text_content()
        if login_text and "登录" in login_text:
            print("🔐🔐 检测到登录按钮，开始登录流程...")
            try:
                await login_btn.click()
                await asyncio.sleep(1)
                
                # 修改：使用新的同意按钮选择器
                agree_btn = await page.query_selector("button.agree-button-od5VVh")
                if agree_btn:
                    await agree_btn.click()
                    print("💬💬 已点击用户协议同意按钮")
                else:
                    print("⚠️⚠️ 未找到同意按钮，可能已自动登录或页面已变化")
                
                # 等待登录按钮消失，表示登录成功
                await page.wait_for_selector("div.login-button-jDhuVc", state="detached", timeout=300000)
                print("🔓🔓 登录成功")
                
                # 新增：登录后检查是否存在关闭按钮
                close_btn = await page.query_selector("span.lv-modal-close-icon")
                if close_btn:
                    await close_btn.click()
                    print("❎❎ 检测到关闭按钮，已点击关闭")
                else:
                    print("ℹ️ℹ️ 未检测到关闭按钮，继续执行")
                    
            except Exception as e:
                print("❌❌ 首次登录流程出错：", e)
                raise
        else:
            print("ℹ️ℹ️ 未检测到需要登录的状态，继续执行")
    else:
        print("🔓🔓 页面无登录按钮，视为已登录状态")

    # 选择视频生成功能
>>>>>>> 48b5ea9 (submit by lue)
    try:
        await page.click("span.lv-select-view-value")
        await asyncio.sleep(1)
        await page.click('span.select-option-label-content-tmGvFs >> text=视频生成')
<<<<<<< HEAD
        
        print("🎬🎬 已切换到视频生成模式")
    except Exception as e:
        print("❌❌ 切换到视频生成模式出错：", e)
    

async def upload_submit_and_wait(page, first_path: str, tail_path: str, user_prompt: str, cycle: int):
    """上传并等待视频生成"""
    
=======
        print("🎬🎬 已切换到视频生成模式")
        await asyncio.sleep(2)  # 等待页面加载完成
        
        # 新增：选择模型 - 首先点击Seedance 2.0元素展开下拉菜单
        seedance_selector = await page.query_selector('div.lv-select-view span.lv-select-view-value:has-text("Seedance 2.0")')
        if seedance_selector:
            await seedance_selector.click()
            print("🔽🔽 已点击Seedance 2.0元素展开模型下拉菜单")
            await asyncio.sleep(1)
            
 # 新增：选择视频 3.0 模型
            # 精确点击包含alt="视频 3.0"的元素
            video_option = await page.query_selector('li.lv-select-option img[alt="视频 3.0"]')
            if video_option:
                option_item = await video_option.evaluate_handle('img => img.closest("li.lv-select-option")')
                if option_item:
                    await option_item.click()
                    print("✅✅ 已选择视频 3.0 模型")
                    await asyncio.sleep(2)
                else:
                    print("⚠️⚠️ 找到图片但无法定位到列表项")
            else:
                # 备用选择器：通过描述文本查找
                video_option_desc = await page.query_selector('li.lv-select-option div.option-description-mvY0uT:has-text("精准响应")')
                if video_option_desc:
                    option_item = await video_option_desc.evaluate_handle('div => div.closest("li.lv-select-option")')
                    if option_item:
                        await option_item.click()
                        print("✅✅ 已通过描述文本选择视频 3.0 模型")
                        await asyncio.sleep(2)
                else:
                    # 备用选择器：通过选项文本查找
                    all_options = await page.query_selector_all('li.lv-select-option')
                    for option in all_options:
                        label_div = await option.query_selector('div.option-label-pa2yfZ')
                        if label_div:
                            label_text = await label_div.text_content()
                            if label_text and label_text.strip() == "视频 3.0":
                                await option.click()
                                print("✅✅ 已通过文本选择视频 3.0 模型")
                                await asyncio.sleep(2)
                                break
                    else:
                        print("⚠️⚠️ 未找到视频 3.0 选项，请检查页面结构")
        else:
            print("⚠️⚠️ 未找到Seedance 2.0元素，可能模型选择已默认设置")
            
    except Exception as e:
        print("❌❌ 初始设置出错：", e)


async def upload_submit_and_wait(page, first_path: str, tail_path: str, user_prompt: str, cycle: int):
    """上传首尾帧图片，填写提示词并提交，等待视频生成完成"""
>>>>>>> 48b5ea9 (submit by lue)
    # 验证文件存在
    if not os.path.exists(first_path):
        raise FileNotFoundError(f"❌❌ 首帧文件不存在: {first_path}")
    if not os.path.exists(tail_path):
        raise FileNotFoundError(f"❌❌ 尾帧文件不存在: {tail_path}")
<<<<<<< HEAD
    
    await page.wait_for_load_state("networkidle")
    
    # 上传首帧
    try:
        print(f"🔍🔍 上传首帧: {os.path.basename(first_path)}")
        
        first_upload_btn_css = "div.reference-upload-h7tmnr.light-Bis76t[style*='--rotate: -8deg']"
        upload_target = await page.query_selector(first_upload_btn_css)
        
        if not upload_target:
            first_upload_btn_xpath = "//div[contains(@class, 'reference-upload-h7tmnr') and contains(@class, 'light-Bis76t') and contains(@style, '--rotate: -8deg')]"
            upload_target = await page.query_selector(first_upload_btn_xpath)
        
=======

    await page.wait_for_load_state("networkidle")

    # 上传首帧图片
    try:
        print(f"🔍🔍 上传首帧: {os.path.basename(first_path)}")
        first_upload_btn_css = "div.reference-upload-h7tmnr.light-Bis76t[style*='--rotate: -8deg']"
        upload_target = await page.query_selector(first_upload_btn_css)
        if not upload_target:
            first_upload_btn_xpath = "//div[contains(@class, 'reference-upload-h7tmnr') and contains(@class, 'light-Bis76t') and contains(@style, '--rotate: -8deg')]"
            upload_target = await page.query_selector(first_upload_btn_xpath)
>>>>>>> 48b5ea9 (submit by lue)
        if not upload_target:
            all_upload_areas = await page.query_selector_all("div.reference-upload-h7tmnr")
            for area in all_upload_areas:
                text = await area.text_content()
                if "首帧" in text:
                    upload_target = area
                    break
<<<<<<< HEAD
        
        if not upload_target:
            raise Exception("无法找到首帧上传区域")
        
=======
        if not upload_target:
            raise Exception("无法找到首帧上传区域")
>>>>>>> 48b5ea9 (submit by lue)
        file_input = await upload_target.query_selector("input[type='file']")
        if not file_input:
            file_inputs = await upload_target.query_selector_all("input[type='file']")
            file_input = file_inputs[0] if file_inputs else None
<<<<<<< HEAD
        
        if not file_input:
            raise Exception("在首帧上传区域找不到文件输入框")
        
        print(f"  文件: {first_path} (存在: {os.path.exists(first_path)}, 大小: {os.path.getsize(first_path)})")
        await file_input.set_input_files(first_path)
        print(f"✅ 首帧上传成功")
        
=======
        if not file_input:
            raise Exception("在首帧上传区域找不到文件输入框")
        print(f"  文件详情: {first_path} (存在: {os.path.exists(first_path)}, 大小: {os.path.getsize(first_path)} 字节)")
        await file_input.set_input_files(first_path)
        print(f"✅ 首帧上传成功")

>>>>>>> 48b5ea9 (submit by lue)
    except Exception as e:
        print(f"❌❌ 上传首帧失败: {e}")
        raise

<<<<<<< HEAD
    # 上传尾帧
    try:
        print(f"🔍🔍 上传尾帧: {os.path.basename(tail_path)}")
        
        tail_upload_btn_css = "div.reference-upload-h7tmnr.light-Bis76t[style*='--rotate: 5deg']"
        tail_target = await page.query_selector(tail_upload_btn_css)
        
        if not tail_target:
            tail_upload_btn_xpath = "//div[contains(@class, 'reference-upload-h7tmnr') and contains(@class, 'light-Bis76t') and contains(@style, '--rotate: 5deg')]"
            tail_target = await page.query_selector(tail_upload_btn_xpath)
        
=======
    # 上传尾帧图片
    try:
        print(f"🔍🔍 上传尾帧: {os.path.basename(tail_path)}")
        tail_upload_btn_css = "div.reference-upload-h7tmnr.light-Bis76t[style*='--rotate: 5deg']"
        tail_target = await page.query_selector(tail_upload_btn_css)
        if not tail_target:
            tail_upload_btn_xpath = "//div[contains(@class, 'reference-upload-h7tmnr') and contains(@class, 'light-Bis76t') and contains(@style, '--rotate: 5deg')]"
            tail_target = await page.query_selector(tail_upload_btn_xpath)
>>>>>>> 48b5ea9 (submit by lue)
        if not tail_target:
            all_upload_areas = await page.query_selector_all("div.reference-upload-h7tmnr")
            for area in all_upload_areas:
                text = await area.text_content()
                if "尾帧" in text:
                    tail_target = area
                    break
<<<<<<< HEAD
        
        if not tail_target:
            raise Exception("无法找到尾帧上传区域")
        
=======
        if not tail_target:
            raise Exception("无法找到尾帧上传区域")
>>>>>>> 48b5ea9 (submit by lue)
        tail_input = await tail_target.query_selector("input[type='file']")
        if not tail_input:
            tail_inputs = await tail_target.query_selector_all("input[type='file']")
            tail_input = tail_inputs[0] if tail_inputs else None
<<<<<<< HEAD
        
        if not tail_input:
            raise Exception("在尾帧上传区域找不到文件输入框")
        
        print(f"  文件: {tail_path} (存在: {os.path.exists(tail_path)}, 大小: {os.path.getsize(tail_path)})")
        await tail_input.set_input_files(tail_path)
        print(f"✅ 尾帧上传成功")
        
=======
        if not tail_input:
            raise Exception("在尾帧上传区域找不到文件输入框")
        print(f"  文件详情: {tail_path} (存在: {os.path.exists(tail_path)}, 大小: {os.path.getsize(tail_path)} 字节)")
        await tail_input.set_input_files(tail_path)
        print(f"✅ 尾帧上传成功")

>>>>>>> 48b5ea9 (submit by lue)
    except Exception as e:
        print(f"❌❌ 上传尾帧失败: {e}")
        raise

<<<<<<< HEAD
    
    # ✅ **最终方案：统一使用首次的prompt选择器**
    try:
        prompt_selector = "textarea.prompt-textarea-l5tJNE"
        
        # 查找所有匹配的元素
        all_prompt_elements = await page.query_selector_all(prompt_selector)
        
        if not all_prompt_elements:
            raise Exception(f"❌❌ 找不到prompt输入框 (选择器: {prompt_selector})")
        
        print(f"  找到 {len(all_prompt_elements)} 个prompt输入框")
        
        # ✅ **统一使用第一个（页面只有一个）**
        prompt_element = all_prompt_elements[0]
        print(f"  使用第一个输入框")
        
        # 验证可见
        is_visible = await prompt_element.is_visible()
        if not is_visible:
            raise Exception("prompt输入框不可见")
        
        await prompt_element.fill(user_prompt)
        print(f"✅ 第{cycle}次任务的Prompt已填写")
        
    except Exception as e:
        print(f"⚠️ 填写Prompt失败: {e}")
        raise
    
    # ✅ **修改：直接使用JavaScript选择视频3.0模型**
    try:
        print("🔍🔍🔍🔍 选择视频 3.0 模型...")
        
        # 直接使用JavaScript选择
        result = await page.evaluate('''() => {
            // 查找包含"视频 3.0"的选项并触发点击
            const options = document.querySelectorAll('div.option-content-ythv8w');
            for (let option of options) {
                if (option.textContent.includes('视频 3.0')) {
                    option.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if result:
            print("✅ 通过JavaScript选择完成")
            await asyncio.sleep(2)
        else:
            print("❌❌ 通过JavaScript选择失败")
        
    except Exception as e:
        print(f"❌❌ 选择视频模型失败: {e}")

    # ✅ **最终方案：统一使用首次的提交按钮**
    try:
        submit_selector = "button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.button-lc3WzE.submit-button-KJTUYS.submit-button-CpjScj"
        
        # 检查按钮是否存在
        submit_button = await page.query_selector(submit_selector)
        if not submit_button:
            raise Exception("找不到提交按钮")
        
        # 等待按钮变为可点击
        print("⏳⏳⏳ 等待提交按钮可用...")
=======
    # 填写提示词
    try:
        prompt_selector = "textarea.prompt-textarea-l5tJNE"
        all_prompt_elements = await page.query_selector_all(prompt_selector)
        if not all_prompt_elements:
            raise Exception(f"❌❌ 找不到Prompt输入框 (选择器: {prompt_selector})")
        print(f"找到 {len(all_prompt_elements)} 个Prompt输入框，使用第一个")
        prompt_element = all_prompt_elements[0]
        is_visible = await prompt_element.is_visible()
        if not is_visible:
            raise Exception("Prompt输入框不可见")
        await prompt_element.fill(user_prompt)
        print(f"✅ 第{cycle}次任务的Prompt已填写")

    except Exception as e:
        print(f"❌❌ 填写Prompt失败: {e}")
        raise

    # 删除之前选择视频3.0模型的JavaScript部分
    print("ℹ️ℹ️ 跳过模型选择步骤（已在initial_setup中完成）")

    # 点击提交按钮
    try:
        submit_selector = "button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.button-lc3WzE.submit-button-KJTUYS.submit-button-CpjScj"
        submit_button = await page.query_selector(submit_selector)
        if not submit_button:
            raise Exception("找不到提交按钮")
        print("⏳⏳⏳ 等待提交按钮变为可用状态...")
>>>>>>> 48b5ea9 (submit by lue)
        for attempt in range(10):
            is_disabled = await submit_button.get_attribute("disabled")
            if not is_disabled:
                break
<<<<<<< HEAD
            print(f"  按钮被禁用，等待1秒... (尝试 {attempt+1}/10)")
            await asyncio.sleep(1)
        
        # 最终检查
        is_disabled = await submit_button.get_attribute("disabled")
        if is_disabled:
            raise Exception("提交按钮持续被禁用")
        
        # 确保按钮在视图中并点击
        await submit_button.scroll_into_view_if_needed()
        await submit_button.click()
        print(f"✅ 第{cycle}次任务提交成功")
        
=======
            print(f"  按钮暂不可用，等待1秒... (尝试 {attempt+1}/10)")
            await asyncio.sleep(1)
        is_disabled = await submit_button.get_attribute("disabled")
        if is_disabled:
            raise Exception("提交按钮持续被禁用")
        await submit_button.scroll_into_view_if_needed()
        await submit_button.click()
        print(f"✅ 第{cycle}次任务提交成功")
>>>>>>> 48b5ea9 (submit by lue)
    except Exception as e:
        print(f"❌❌ 提交失败: {e}")
        raise

    print("⏳⏳⏳ 等待视频生成...")
<<<<<<< HEAD

    # 检测新视频
    await asyncio.sleep(5)
    last_urls = await get_all_video_srcs(page)
    seconds_elapsed = 0
    MAX_WAIT = 600  # 最多等待10分钟
=======
    # 检测新生成的视频
    await asyncio.sleep(5)
    last_urls = await get_all_video_srcs(page)
    seconds_elapsed = 0
    MAX_WAIT = 600  # 最大等待时间10分钟
>>>>>>> 48b5ea9 (submit by lue)

    while seconds_elapsed < MAX_WAIT:
        await asyncio.sleep(1)
        seconds_elapsed += 1
        current_urls = await get_all_video_srcs(page)
        new_urls = [url for url in current_urls if url not in last_urls]

        if new_urls:
            final_url = new_urls[-1]
<<<<<<< HEAD
            print(f"✅ 检测到新视频: {final_url[:80]}...")
=======
            print(f"✅ 检测到新生成的视频: {final_url[:80]}...")
>>>>>>> 48b5ea9 (submit by lue)
            if not final_url.startswith(('http://', 'https://')):
                final_url = urljoin(page.url, final_url)
            return final_url

        if seconds_elapsed % 10 == 0:
            print(f"⏳⏳⏳ 已等待 {seconds_elapsed} 秒...")

    raise TimeoutError(f"等待视频生成超时（{MAX_WAIT}秒）")


async def generate_videos(photos, prompts):
<<<<<<< HEAD
    """主流程"""
    print("🔍🔍 开始检查图片尺寸...")
    adjusted_photos = check_and_adjust_image_size(photos)
    
    pairs = [(adjusted_photos[i], adjusted_photos[i + 1]) for i in range(0, len(adjusted_photos), 2)]
    saved_paths = []
    
    # 临时目录路径
    temp_dir = os.path.join(SCRIPT_DIR, "temp_adjusted_images")
    
    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR, 
=======
    """主流程：调整图片尺寸，登录并循环处理图片对以生成视频"""
    print("🔍🔍 开始检查并调整图片尺寸...")
    adjusted_photos, temp_img_dir = check_and_adjust_image_size(photos)

    pairs = [(adjusted_photos[i], adjusted_photos[i + 1]) for i in range(0, len(adjusted_photos), 2)]
    saved_paths = []

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
>>>>>>> 48b5ea9 (submit by lue)
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            await asyncio.sleep(2)
<<<<<<< HEAD
            
=======

>>>>>>> 48b5ea9 (submit by lue)
            if context.pages:
                page = context.pages[0]
                await page.wait_for_load_state('domcontentloaded')
            else:
                page = await context.new_page()
<<<<<<< HEAD
                
            # ✅ **只在开始前设置一次初始状态**
=======

            # 初始设置（登录和模式切换）
>>>>>>> 48b5ea9 (submit by lue)
            await initial_setup(page)

            # 任务循环
            cycle = 1
            for idx, (first_path, tail_path) in enumerate(pairs, start=1):
                user_prompt = prompts[idx - 1] if idx - 1 < len(prompts) else prompts[-1]
<<<<<<< HEAD
                print(f"\n=== 任务 {idx}/{len(pairs)} (cycle={cycle}) ===")
                print(f"  首帧: {os.path.basename(first_path)}")
                print(f"  尾帧: {os.path.basename(tail_path)}")
=======
                print(f"\n=== 开始处理第 {idx}/{len(pairs)} 个任务 (cycle={cycle}) ===")
                print(f"  首帧图片: {os.path.basename(first_path)}")
                print(f"  尾帧图片: {os.path.basename(tail_path)}")
>>>>>>> 48b5ea9 (submit by lue)

                try:
                    video_url = await upload_submit_and_wait(page, first_path, tail_path, user_prompt, cycle)

<<<<<<< HEAD
                    # 下载视频
=======
                    # 下载生成的视频
>>>>>>> 48b5ea9 (submit by lue)
                    save_name = f"{os.path.splitext(OUTPUT_FILENAME)[0]}_{cycle}.mp4"
                    save_path = os.path.join(OUTPUT_DIR, save_name)

                    async with aiohttp.ClientSession() as session:
                        await download_file(session, video_url, save_path)

                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        saved_paths.append(save_path)
<<<<<<< HEAD
                        print(f"✅ 成功: {save_path} ({os.path.getsize(save_path)} bytes)")
                    else:
                        print(f"❌❌ 视频文件为空，跳过此任务: {save_path}")
=======
                        print(f"✅ 视频片段保存成功: {save_path} ({os.path.getsize(save_path)} 字节)")
                    else:
                        print(f"⚠️ 视频文件为空，跳过此任务: {save_path}")
>>>>>>> 48b5ea9 (submit by lue)

                except Exception as e:
                    print(f"❌❌ 任务 {idx} 失败，跳过: {e}")

<<<<<<< HEAD
                # 每次任务后刷新页面（除了最后一次）
=======
                # 每次任务后刷新页面（最后一次除外）
>>>>>>> 48b5ea9 (submit by lue)
                if idx < len(pairs):
                    print("🔄🔄 刷新页面准备下一个任务...")
                    await page.reload()
                    await asyncio.sleep(3)
                    print("🔄🔄 重新配置视频生成模式...")
                    await initial_setup(page)

                cycle += 1

            await context.close()

    finally:
<<<<<<< HEAD
        # 清理临时文件
        if os.path.exists(temp_dir):
            print(f"🗑️ 清理临时目录: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
=======
        # 修改：无论成功与否，都清理临时图片目录
        if temp_img_dir and os.path.exists(temp_img_dir):
            print(f"🗑🗑️ 清理临时图片目录: {temp_img_dir}")
            try:
                shutil.rmtree(temp_img_dir, ignore_errors=True)
                print("✅ 临时图片目录已删除")
            except Exception as e:
                print(f"⚠️ 删除临时目录时出错 (将忽略): {e}")
>>>>>>> 48b5ea9 (submit by lue)

    if not saved_paths:
        raise RuntimeError("所有视频片段均生成失败，没有可拼接的视频")

<<<<<<< HEAD
    print(f"\n✅ 完成！成功下载 {len(saved_paths)}/{len(pairs)} 个视频片段")
=======
    print(f"\n✅ 处理完成！成功生成 {len(saved_paths)}/{len(pairs)} 个视频片段")
>>>>>>> 48b5ea9 (submit by lue)
    return saved_paths


def main():
<<<<<<< HEAD
    """CLI主函数"""
    parser = argparse.ArgumentParser(description="Generate videos via Jimeng using photos & prompts")
    parser.add_argument("--photos", nargs="+", required=True, help="List of photo file paths")
    parser.add_argument("--prompts", nargs="+", required=True, help="Corresponding list of prompts (one per pair)")
    args = parser.parse_args()
    
    if len(args.photos) % 2 != 0:
        raise ValueError("照片数量必须是偶数")
    
    n_pairs = len(args.photos) // 2
    if len(args.prompts) < n_pairs:
        args.prompts.extend([args.prompts[-1]] * (n_pairs - len(args.prompts)))
    
    print("🔍🔍 开始检查图片尺寸一致性...")
    print(f"📋📋 输入文件: {args.photos}")
    
=======
    """CLI主函数：解析参数并启动视频生成流程"""
    parser = argparse.ArgumentParser(description="使用即梦AI，通过上传图片对和提示词生成视频")
    parser.add_argument("--photos", nargs="+", required=True, help="图片文件路径列表（必须为偶数）")
    parser.add_argument("--prompts", nargs="+", required=True, help="对应的提示词列表（每个图片对一个，不足则复用最后一个）")
    args = parser.parse_args()

    if len(args.photos) % 2 != 0:
        raise ValueError("图片数量必须是偶数")

    n_pairs = len(args.photos) // 2
    if len(args.prompts) < n_pairs:
        args.prompts.extend([args.prompts[-1]] * (n_pairs - len(args.prompts)))

    print("🔍🔍 开始检查输入图片...")
    print(f"输入文件列表: {args.photos}")

>>>>>>> 48b5ea9 (submit by lue)
    # 验证所有输入文件存在
    for path in args.photos:
        if not os.path.exists(path):
            raise FileNotFoundError(f"❌❌ 输入文件不存在: {path}")
        print(f"  ✓ {path}")
<<<<<<< HEAD
    
    adjusted_photos = check_and_adjust_image_size(args.photos)
    print(f"📁📁 调整后文件: {adjusted_photos}")
    
=======

    adjusted_photos, temp_img_dir_from_main = check_and_adjust_image_size(args.photos)
    print(f"调整后的文件列表: {adjusted_photos}")

>>>>>>> 48b5ea9 (submit by lue)
    photos_input = adjusted_photos
    prompts_input = args.prompts[:n_pairs]

    try:
        saved_paths = asyncio.run(generate_videos(photos_input, prompts_input))
        final_output_abs = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

<<<<<<< HEAD
=======
        # 修改：确保在主流程结束后也清理可能存在的临时目录
        if temp_img_dir_from_main and os.path.exists(temp_img_dir_from_main):
            print(f"🗑🗑️ 主函数中清理临时目录: {temp_img_dir_from_main}")
            shutil.rmtree(temp_img_dir_from_main, ignore_errors=True)

        # 处理生成的视频片段：单个则移动，多个则拼接
>>>>>>> 48b5ea9 (submit by lue)
        if len(saved_paths) == 1:
            src = saved_paths[0]
            if os.path.abspath(src) != os.path.abspath(final_output_abs):
                os.makedirs(os.path.dirname(final_output_abs), exist_ok=True)
                try:
                    os.replace(src, final_output_abs)
                except Exception:
                    shutil.copy2(src, final_output_abs)
                    try:
                        os.remove(src)
                    except Exception:
                        pass
<<<<<<< HEAD
            print(f"FINAL VIDEO PATH: {final_output_abs}")
            return final_output_abs

        # 拼接视频
=======
            print(f"✅ 最终视频路径: {final_output_abs}")
            return final_output_abs

>>>>>>> 48b5ea9 (submit by lue)
        if len(saved_paths) > 1:
            list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for path in saved_paths:
                    f.write(f"file '{os.path.abspath(path)}'\n")
<<<<<<< HEAD
            
=======

>>>>>>> 48b5ea9 (submit by lue)
            cmd = [
                FFMPEG_CMD, "-f", "concat", "-safe", "0", "-i", list_file,
                "-c", "copy", "-y", final_output_abs
            ]
            subprocess.run(cmd, check=True)

<<<<<<< HEAD
            # 清理
            for p in saved_paths:
                os.remove(p)
            os.remove(list_file)
        
        print(f"FINAL VIDEO PATH: {final_output_abs}")
        return final_output_abs

    except Exception as e:
        print(f"视频生成失败: {e}")
=======
            # 清理临时视频文件和列表文件
            for p in saved_paths:
                os.remove(p)
            os.remove(list_file)

        print(f"✅ 最终视频路径: {final_output_abs}")
        return final_output_abs

    except Exception as e:
        print(f"❌❌ 视频生成流程失败: {e}")
>>>>>>> 48b5ea9 (submit by lue)
        raise


if __name__ == "__main__":
    main()