import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import argparse
import subprocess
import shutil

# ================== 配置区（唯一保存方法） ==================
# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 最终与中间文件统一保存到：脚本同目录下的 static/video（相对路径）
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "static", "video")
OUTPUT_FILENAME = "generated_video.mp4"  # 最终文件名（固定）
MAX_WAIT_SECONDS = 1000

# ffmpeg 可执行名（假设在 PATH）；如需使用自定义路径，请直接替换为绝对路径字符串
FFMPEG_CMD = "ffmpeg"

# profile 存放在脚本同目录下的 playwright_profile
PROFILE_DIR = os.path.join(SCRIPT_DIR, "playwright_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)
# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ==========================================================


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
    print(f"✅ 文件已保存至 {save_path}")


# ========== initial_setup：首次按原流程登录；后续自动跳过 ==========
async def initial_setup(page):
    JIMENG_URL = "https://jimeng.jianying.com/ai-tool/home/"
    await page.goto(JIMENG_URL)
    await asyncio.sleep(1)

    # 检测登录按钮是否存在：若存在，说明可能未登录，需要执行首次登录逻辑
    login_btn = await page.query_selector("div.login-button-tP78Sd")
    if login_btn:
        print("🔐 未检测到已登录状态，开始首次登录流程（将点击登录并等待你手动扫码/登录）...")
        try:
            await login_btn.click()
            await asyncio.sleep(0.6)
            agree_btn = await page.query_selector("button.agree-button-G3z4aB")
            if agree_btn:
                try:
                    await agree_btn.click()
                    print("💬 已点击同意按钮")
                except Exception:
                    print("⚠️ 点击同意按钮失败或按钮已自动消失")

            try:
                await page.wait_for_selector("div.login-button-tP78Sd", state="detached", timeout=300000)
                print("✅ 登录完成或登录按钮已消失（首次登录）")
            except PlaywrightTimeoutError:
                print("⚠️ 等待登录超时（300s），可能需手动确认已登录或检查网络/页面")
        except Exception as e:
            print("❌ 首次登录流程出错：", e)
            raise
    else:
        print("🔓 已检测到登录状态（复用 profile），跳过首次登录步骤")

    # 尝试切换到视频生成模式（容错）
    try:
        await page.click("span.lv-select-view-value")
        await asyncio.sleep(0.8)
        await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
        await asyncio.sleep(0.8)
        await page.click('(//div[contains(@class,"lv-select-view")])[2]')
        await asyncio.sleep(0.8)
        await page.click('//span[contains(text(),"5s")]')
        await asyncio.sleep(0.5)
        print("🎬 已切换到视频生成模式")
    except Exception as e:
        print("⚠️ 切换到视频生成模式时出现问题（可能选择器失效）：", e)


# ========== 上传、提交并等待生成 ==========
async def upload_submit_and_wait(page, first_path: str, tail_path: str, user_prompt: str, cycle: int):
    # 上传首帧图片
    first_upload_btn = "div.reference-upload-eclumn.reference-KpBKPw.light-i454GW[style*='--rotate: -8deg']"
    upload_target = await page.query_selector(first_upload_btn)
    if not upload_target:
        raise RuntimeError(f"无法找到首帧上传按钮：{first_upload_btn}")
    file_input = await upload_target.query_selector("input[type='file']")
    if not file_input:
        raise RuntimeError("首帧上传控件中未找到 input[type=file]")
    await file_input.set_input_files(first_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", file_input)
    print(f"✅ 首帧图片已上传：{first_path}")

    # 上传尾帧图片
    tail_upload_btn = "div.reference-upload-eclumn.reference-KpBKPw.light-i454GW[style*='--rotate: 5deg']"
    tail_target = await page.query_selector(tail_upload_btn)
    if not tail_target:
        raise RuntimeError(f"无法找到尾帧上传按钮：{tail_upload_btn}")
    tail_input = await tail_target.query_selector("input[type='file']")
    if not tail_input:
        raise RuntimeError("尾帧上传控件中未找到 input[type=file]")
    await tail_input.set_input_files(tail_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", tail_input)
    print(f"✅ 尾帧图片已上传：{tail_path}")

    # 填写 prompt（容错：若指定选择器失效则填第一个 textarea）
    try:
        await page.fill("textarea.lv-textarea.prompt-textarea-XfqAoB", user_prompt)
    except Exception:
        ta = await page.query_selector("textarea")
        if ta:
            await ta.fill(user_prompt)
        else:
            raise RuntimeError("无法找到 prompt 输入框（textarea）")
    print("✅ prompt 已填写")

    # 点击生成按钮（区分 cycle）
    if cycle == 1:
        primary_submit_selector = "button.submit-button-VW0U_J"
        try:
            await page.click(primary_submit_selector)
        except Exception:
            pass

        try:
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
            print("⚠️ 未在限定时间内找到“生成”确认按钮，继续等待生成结果。")
    else:
        second_submit_btn_selector = "button.submit-button-M82Oxj"
        try:
            await page.click(second_submit_btn_selector)
        except Exception:
            print("⚠️ 未能点击第二类提交按钮，继续等待可能的生成流程。")

    print("⏳ 已提交，开始检测新视频出现...（等待中）")

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
                print(f"✅ 检测到新视频: {url}")
            return new_urls[-1]
        if seconds_elapsed % 2 == 0:
            print(f"⏳ 已等待 {seconds_elapsed} 秒，尚未检测到新视频...")
        if seconds_elapsed >= MAX_WAIT_SECONDS:
            raise Exception(f"超时未检测到新视频（已等待 {MAX_WAIT_SECONDS} 秒）")


# ========== 主流程：使用持久化 profile（launch_persistent_context） ==========
async def generate_videos(photos, prompts):
    # 确保输出目录存在（脚本目录下的 static/video）
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pairs = [(photos[i], photos[i + 1]) for i in range(0, len(photos), 2)]
    if len(pairs) == 0:
        raise ValueError("无法从 photos 中生成任何配对（需要偶数张，至少 2 张）")

    saved_paths = []
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(user_data_dir=PROFILE_DIR, headless=False)
        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()

        await initial_setup(page)

        cycle = 1
        for idx, (first_path, tail_path) in enumerate(pairs, start=1):
            user_prompt = prompts[idx - 1] if idx - 1 < len(prompts) else prompts[-1]

            print(f"\n=== 开始第 {idx} 个生成任务（{first_path} -> {tail_path}），cycle = {cycle} prompt: {user_prompt} ===")
            video_url = await upload_submit_and_wait(page, first_path, tail_path, user_prompt, cycle)

            # 保存为明确的临时文件名：generated_video_{cycle}.mp4
            save_name = f"{os.path.splitext(OUTPUT_FILENAME)[0]}_{cycle}.mp4"
            save_path = os.path.join(OUTPUT_DIR, save_name)

            async with aiohttp.ClientSession() as session:
                await download_file(session, video_url, save_path)

            saved_paths.append(save_path)

            # 若有后续任务，重新准备页面继续
            if idx < len(pairs):
                await asyncio.sleep(2)
                await page.reload()
                await asyncio.sleep(6)
                try:
                    await page.click("div[aria-hidden='true'].lv-select-suffix")
                    await asyncio.sleep(0.8)
                    await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
                    await asyncio.sleep(0.8)
                except Exception:
                    print("⚠️ 重新准备页面时未能切换到视频生成，请手动确认页面状态或更新选择器。")
            cycle += 1

        await context.close()

    print("\n✅ 所有视频已生成并下载完成")
    return saved_paths


# ========== CLI 主函数（固定最终保存位置） ==========
def main():
    parser = argparse.ArgumentParser(description="Generate videos via Jimeng using photos & prompts")
    parser.add_argument("--photos", nargs="+", required=True, help="List of photo file paths (even number)")
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

        # 统一最终输出路径：脚本同目录下 static/video/generated_video.mp4
        final_output_abs = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        # 如果只有一个生成文件：直接重命名/移动为 final_output_abs（覆盖）
        if len(saved_paths) == 1:
            src = saved_paths[0]
            if os.path.abspath(src) != os.path.abspath(final_output_abs):
                # 先确保目录存在
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

        # 多个文件：使用 ffmpeg concat 在同一目录拼接为 final_output_abs
        list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for path in saved_paths:
                # 使用绝对路径写入 concat 列表，ffmpeg 要求每行: file 'path'
                f.write(f"file '{os.path.abspath(path)}'\n")

        # 调用 ffmpeg 拼接（输出到 final_output_abs，覆盖同名）
        cmd = [
            FFMPEG_CMD, "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", "-y", final_output_abs
        ]
        subprocess.run(cmd, check=True)

        # 清理中间文件与列表
        for p in saved_paths:
            try:
                os.remove(p)
            except Exception:
                pass
        try:
            os.remove(list_file)
        except Exception:
            pass

        print(f"拼接完成：{final_output_abs}")
        print(f"FINAL VIDEO PATH: {final_output_abs}")
        return final_output_abs

    except Exception as e:
        print(f"视频生成失败: {e}")
        raise


if __name__ == "__main__":
    main()
