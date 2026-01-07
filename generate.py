import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import argparse
import subprocess
import shutil
from urllib.parse import urljoin


# 脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 视频目录（相对路径）
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "static", "video")
OUTPUT_FILENAME = "generated_video.mp4"  

#基础配置
FFMPEG_CMD = "ffmpeg"
PROFILE_DIR = os.path.join(SCRIPT_DIR, "playwright_profile")



#获取页面所有视频链接
async def get_all_video_srcs(page):
    page_url = page.url
    sources = await page.query_selector_all("video source[src]")
    srcs = set()
    for s in sources:
        url = await s.get_attribute("src")
        if url:
            if url.startswith(('http://', 'https://')):
                srcs.add(url)
            else:
                absolute_url = urljoin(page_url, url)
                srcs.add(absolute_url)
    videos = await page.query_selector_all("video[src]")
    for v in videos:
        url = await v.get_attribute("src")
        if url:
            if url.startswith(('http://', 'https://')):
                srcs.add(url)
            else:
                absolute_url = urljoin(page_url, url)
                srcs.add(absolute_url)
    
    return list(srcs)


#下载视频
async def download_file(session, url, save_path):
    try:
        print(f"📥📥 开始下载: {url}")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        timeout = aiohttp.ClientTimeout(total=300)  
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 64)
                    if not chunk:
                        break
                    f.write(chunk)
        
        print(f"✅ 文件已保存至 {save_path})")

            
    except Exception as e:
        print(f"❌下载失败: {e}")


# 首次登陆即梦ai流程（无profile）
async def initial_setup(page):
    JIMENG_URL = "https://jimeng.jianying.com/ai-tool/home/"
    await page.goto(JIMENG_URL)
    await asyncio.sleep(1)

    # 检测登录按钮是否存在
    login_btn = await page.query_selector("div.login-button-tP78Sd")
    if login_btn:
        try:
            await login_btn.click()
            await asyncio.sleep(0.6)
            agree_btn = await page.query_selector("button.agree-button-G3z4aB")
            if agree_btn:
                await agree_btn.click()
                print("💬💬💬💬 已点击同意按钮")
   
            await page.wait_for_selector("div.login-button-tP78Sd", state="detached", timeout=300000)
  

        except Exception as e:
            print("❌ 首次登录流程出错：", e)
            raise
    else:
        print("🔓已检测到登录状态，跳过首次登录步骤")

    # 切换到视频生成模式
    try:
        await page.click("span.lv-select-view-value")
        await asyncio.sleep(0.8)
        await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
        await asyncio.sleep(0.8)
        await page.click('(//div[contains(@class,"lv-select-view")])[2]')
        await asyncio.sleep(0.8)
        await page.click('//span[contains(text(),"5s")]')
        await asyncio.sleep(0.5)
        print("🎬已切换到视频生成模式")
    except Exception as e:
        print("❌ 切换到视频生成模式时出现问题：", e)


# 即梦ai视频生成任务
async def upload_submit_and_wait(page, first_path: str, tail_path: str, user_prompt: str, cycle: int):

    # 上传首帧图片 
    first_upload_btn = "div.reference-upload-eclumn.light-i454GW[style*='--rotate: -8deg']"
    upload_target = await page.query_selector(first_upload_btn)
    file_input = await upload_target.query_selector("input[type='file']")
    await file_input.set_input_files(first_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", file_input)
    print(f"✅ 首帧图片已上传：{first_path}")

    # 上传尾帧图片
    tail_upload_btn = "div.reference-upload-eclumn.light-i454GW[style*='--rotate: 5deg']"
    tail_target = await page.query_selector(tail_upload_btn)
    tail_input = await tail_target.query_selector("input[type='file']")
    await tail_input.set_input_files(tail_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", tail_input)
    print(f"✅ 尾帧图片已上传：{tail_path}")

    # 填写视频指令
    await page.fill("textarea.lv-textarea.prompt-textarea-XfqAoB", user_prompt)
    print("✅ 视频指令已填写")

    # 提交任务（分轮次）
    if cycle == 1:
        primary_submit_selector = "button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.submit-button-M82Oxj"
        try:
            await page.click(primary_submit_selector)
            locator = page.locator("div.content-wt4FUb:has-text('生成')")
            await locator.wait_for(state="visible", timeout=60000)
            await locator.scroll_into_view_if_needed()
            await locator.hover()
            await asyncio.sleep(0.12)
            box = await locator.bounding_box()
            if box:
                center_x = box["x"] + box["width"] / 2
                center_y = box["y"] + box["height"] / 2
                await page.mouse.move(center_x, center_y)
                await asyncio.sleep(0.05)
                await page.mouse.click(center_x, center_y)
            else:
                await locator.click()
        except PlaywrightTimeoutError:
            print("⚠️ 未在限定时间内找到生成确认按钮。")

    else:
        second_submit_btn_selector = "button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.button-wtoV7J.submit-button-VW0U_J.submit-button-M82Oxj"
        try:
            await page.click(second_submit_btn_selector)
        except Exception:
            print("⚠️ 未能点击第二类提交按钮。")

    print("⏳⏳⏳⏳⏳⏳⏳⏳⏳⏳⏳⏳⏳⏳")

    # 检测新视频出现
    await asyncio.sleep(5)
    last_urls = await get_all_video_srcs(page)
    seconds_elapsed = 0

    while True:
        await asyncio.sleep(1)
        seconds_elapsed += 1
        current_urls = await get_all_video_srcs(page)
        new_urls = [url for url in current_urls if url not in last_urls]
        if new_urls:
            for url in new_urls:
                print(f"✅ 检测到新视频！")
            final_url = new_urls[-1]

            #转换为绝对路径
            if not final_url.startswith(('http://', 'https://')):
                final_url = urljoin(page.url, final_url)
            return final_url
        
        if seconds_elapsed % 10 == 0:  
            print(f"⏳ 已等待 {seconds_elapsed} 秒，尚未检测到新视频...")



# 爬虫主流程函数
async def generate_videos(photos, prompts):
    pairs = [(photos[i], photos[i + 1]) for i in range(0, len(photos), 2)]
    saved_paths = []
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR, 
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
        if context.pages:
            page = context.pages[0]
            await page.wait_for_load_state('domcontentloaded')
        else:
            page = await context.new_page()
        await initial_setup(page)

        #视频生成任务循环
        cycle = 1
        for idx, (first_path, tail_path) in enumerate(pairs, start=1):
            user_prompt = prompts[idx - 1] if idx - 1 < len(prompts) else prompts[-1]
            print(f"\n=== 开始第 {idx} 个生成任务（{first_path} -> {tail_path}），cycle = {cycle} prompt: {user_prompt} ===")
            video_url = await upload_submit_and_wait(page, first_path, tail_path, user_prompt, cycle)

            # 保存结果视频临时文件名：generated_video_{cycle}.mp4
            save_name = f"{os.path.splitext(OUTPUT_FILENAME)[0]}_{cycle}.mp4"
            save_path = os.path.join(OUTPUT_DIR, save_name)
            async with aiohttp.ClientSession() as session:
                await download_file(session, video_url, save_path)
            saved_paths.append(save_path)

            # 刷新页面继续后续任务
            if idx < len(pairs):
                await asyncio.sleep(2)
                await page.reload()
                await asyncio.sleep(4)
                await page.click("div[aria-hidden='true'].lv-select-suffix")
                await asyncio.sleep(0.8)
                await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
                await asyncio.sleep(0.8)
            cycle += 1

        await context.close()
    print("\n✅ 所有视频已生成并下载完成")
    return saved_paths


#CLI主函数
def main():
    parser = argparse.ArgumentParser(description="Generate videos via Jimeng using photos & prompts")
    parser.add_argument("--photos", nargs="+", required=True, help="List of photo file paths")
    parser.add_argument("--prompts", nargs="+", required=True, help="Corresponding list of prompts (one per pair)")
    args = parser.parse_args()
    if len(args.photos) % 2 != 0:
        raise ValueError("Number of photos must be even (paired for first/tail frame).")
    n_pairs = len(args.photos) // 2
    if len(args.prompts) < n_pairs:
        args.prompts.extend([args.prompts[-1]] * (n_pairs - len(args.prompts)))
    photos_input = args.photos
    prompts_input = args.prompts[:n_pairs]

    try:
        saved_paths = asyncio.run(generate_videos(photos_input, prompts_input))
        final_output_abs = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

        # 如果只有一个生成文件直接覆盖
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
            print(f"FINAL VIDEO PATH: {final_output_abs}")
            return final_output_abs

        # 使用 ffmpeg concat 在同一目录拼接为 final_output
        list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for path in saved_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        cmd = [
            FFMPEG_CMD, "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", "-y", final_output_abs
        ]
        subprocess.run(cmd, check=True)

        # 清理中间文件与列表
        for p in saved_paths:
            os.remove(p)
        os.remove(list_file)
        print(f"拼接完成！FINAL VIDEO PATH: {final_output_abs}")
        return final_output_abs

    except Exception as e:
        print(f"视频生成失败: {e}")
        raise

    #事件循环清理(必须要try-excpet)
    finally:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.stop()
            if not loop.is_closed():
                loop.close()
        except:
            pass


if __name__ == "__main__":
    main()