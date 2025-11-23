import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright
import argparse

# 基础配置
OUTPUT_DIR = r"D:\File\大四上\story-prototype\static\video"  # 修改后的目录
OUTPUT_FILENAME = "generated_video.mp4"
MAX_WAIT_SECONDS = 1000  

# async def get_all_video_srcs(page):
#     videos = await page.query_selector_all("video")
#     srcs = set()
#     for v in videos:
#         s = await v.get_attribute("src")
#         if s:
#             srcs.add(s)
#     return list(srcs)
async def get_all_video_srcs(page):
    # 方案 1：查 video > source[src]
    sources = await page.query_selector_all("video source[src]")
    srcs = set()
    for s in sources:
        url = await s.get_attribute("src")
        if url:
            srcs.add(url)
    # 方案 2：兜底查 video[src]
    videos = await page.query_selector_all("video[src]")
    for v in videos:
        url = await v.get_attribute("src")
        if url:
            srcs.add(url)
    return list(srcs)


async def download_file(session, url, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 确保目录存在
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            while True:
                chunk = await resp.content.read(1024 * 64)
                if not chunk:
                    break
                f.write(chunk)
    print(f"文件已保存至 {save_path}")


async def initial_setup(page):
    JIMENG_URL = "https://jimeng.jianying.com/ai-tool/home/"
    await page.goto(JIMENG_URL)

    # 点击登录按钮
    await page.click("div.login-button-tP78Sd")
    await page.click("button.agree-button-G3z4aB")
    print("已点击登录按钮")

    await page.wait_for_selector("div.login-button-tP78Sd", state="detached", timeout=300000)
    print("登录或登录等待完成")

    # 切换到视频生成模式
    await page.click("span.lv-select-view-value")
    await asyncio.sleep(1)
    await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
    await asyncio.sleep(1)
    await page.click('(//div[contains(@class,"lv-select-view")])[2]')
    await asyncio.sleep(1)
    await page.click('//span[contains(text(),"5s")]')
    await asyncio.sleep(0.5)
    print("已切换到视频生成模式")


async def upload_submit_and_wait(page, first_path: str, tail_path: str, user_prompt: str, cycle: int):
    # 上传首帧图片
    first_upload_btn = "div.reference-upload-eclumn.reference-KpBKPw.light-i454GW[style*='--rotate: -8deg']"
    upload_target = await page.query_selector(first_upload_btn)
    file_input = await upload_target.query_selector("input[type='file']")
    await file_input.set_input_files(first_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", file_input)
    print(f"首帧图片已上传：{first_path}")

    # 上传尾帧图片
    tail_upload_btn = "div.reference-upload-eclumn.reference-KpBKPw.light-i454GW[style*='--rotate: 5deg']"
    tail_target = await page.query_selector(tail_upload_btn)
    tail_input = await tail_target.query_selector("input[type='file']")
    await tail_input.set_input_files(tail_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", tail_input)
    print(f"尾帧图片已上传：{tail_path}")

    # 填写 prompt
    await page.fill("textarea.lv-textarea.prompt-textarea-XfqAoB", user_prompt)
    print("prompt 已填写")

    # 点击生成按钮
    if cycle == 1:
        primary_submit_selector = "button.submit-button-VW0U_J"
        await page.click(primary_submit_selector)
        await asyncio.sleep(0.8)
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
    else:
        second_submit_btn_selector = "button.submit-button-M82Oxj"
        await page.click(second_submit_btn_selector)

    print("已提交，开始生成视频（等待检测新视频）")

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
                print(f"检测到新视频: {url}")
            return new_urls[-1]
        if seconds_elapsed % 2 == 0:
            print(f"已等待 {seconds_elapsed} 秒，尚未检测到新视频...")
        if seconds_elapsed >= MAX_WAIT_SECONDS:
            raise Exception(f"超时未检测到新视频（已等待 {MAX_WAIT_SECONDS} 秒）")


async def generate_videos(photos, prompts):
    os.makedirs(OUTPUT_DIR, exist_ok=True)  # 确保输出目录存在
    pairs = [(photos[i], photos[i+1]) for i in range(0, len(photos), 2)]
    if len(pairs) == 0:
        raise ValueError("无法从 photos 中生成任何配对（需要偶数张，至少 2 张）")

    saved_paths = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await initial_setup(page)
        cycle = 1
        for idx, (first_path, tail_path) in enumerate(pairs, start=1):
            user_prompt = prompts[idx-1] if idx-1 < len(prompts) else prompts[-1]

            print(f"\n=== 开始第 {idx} 个生成任务（{first_path} -> {tail_path}），cycle = {cycle} prompt: {user_prompt} ===")
            video_url = await upload_submit_and_wait(page, first_path, tail_path, user_prompt, cycle)

            save_name = OUTPUT_FILENAME if cycle == 1 else f"{os.path.splitext(OUTPUT_FILENAME)[0]}_{cycle}.mp4"
            save_path = os.path.join(OUTPUT_DIR, save_name)

            async with aiohttp.ClientSession() as session:
                await download_file(session, video_url, save_path)

            saved_paths.append(save_path)

            if idx < len(pairs):
                await asyncio.sleep(2)
                await page.reload()
                await asyncio.sleep(6)
                await page.click("div[aria-hidden='true'].lv-select-suffix")
                await asyncio.sleep(0.8)
                await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
                await asyncio.sleep(0.8)
            cycle += 1

        await context.close()
        await browser.close()

    print("\n所有视频已生成并下载完成")
    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="Generate videos via Jimeng using photos & prompts")
    parser.add_argument("--photos", nargs="+", required=True, help="List of photo file paths (even number)")
    parser.add_argument("--prompts", nargs="+", required=True, help="Corresponding list of prompts (one per pair)")
    parser.add_argument("--output", default=os.path.join(OUTPUT_DIR, OUTPUT_FILENAME), help="Output MP4 path")
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
        if len(saved_paths) > 1:
            final_output = args.output
            list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for path in saved_paths:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            import subprocess
            ffmpeg_path = r"D:/File/大四上/ffmpeg-8.0-essentials_build/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe"
            subprocess.run([
                ffmpeg_path, "-f", "concat", "-safe", "0", "-i", list_file,
                "-c", "copy", "-y", final_output
            ], check=True)
            for p in saved_paths:
                os.remove(p)
            print(f"拼接完成：{final_output}")
            print(f"FINAL VIDEO PATH: {final_output}")
            return final_output
        else:
            final_path = saved_paths[0]
            if final_path != args.output:
                os.replace(final_path, args.output)
                final_path = args.output
            print(f"FINAL VIDEO PATH: {final_path}")
            return final_path
    except Exception as e:
        print(f"视频生成失败: {e}")
        raise


if __name__ == "__main__":
    main()
