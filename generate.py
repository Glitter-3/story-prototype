import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright

# 基础配置
JIMENG_URL = "https://jimeng.jianying.com/ai-tool/home/"
OUTPUT_DIR = r"C:\Users\Administrator\Desktop"
OUTPUT_FILENAME = "generated_video.mp4"
MAX_WAIT_SECONDS = 1000  

async def get_all_video_srcs(page):
    videos = await page.query_selector_all("video")
    srcs = set()
    for v in videos:
        s = await v.get_attribute("src")
        if s:
            srcs.add(s)
    return list(srcs)


async def download_file(session, url, save_path):
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            while True:
                chunk = await resp.content.read(1024 * 64)
                if not chunk:
                    break
                f.write(chunk)
    print(f"✅ 文件已保存至 {save_path}")


# 初次的页面导航
async def initial_setup(page):
    await page.goto(JIMENG_URL)

    # 点击登录按钮
    await page.click("div.login-button-tP78Sd")
    await page.click("button.agree-button-G3z4aB")
    print("✅ 已点击登录按钮")

    # 等待登录完成
    await page.wait_for_selector("div.login-button-tP78Sd", state="detached", timeout=300000)
    print("✅ 登录或登录等待完成")

    # 切换到视频生成模式
    await page.click("span.lv-select-view-value")
    await asyncio.sleep(1)
    await page.click('span.select-option-label-content-FJbQrO >> text=视频生成')
    await asyncio.sleep(1)
    await page.click('(//div[contains(@class,"lv-select-view")])[2]')
    await asyncio.sleep(1)
    await page.click('//span[contains(text(),"5s")]')
    await asyncio.sleep(0.5)
    print("✅ 已切换到视频生成模式")


# 视频生成
async def upload_submit_and_wait(page, first_path: str, tail_path: str, user_prompt: str, cycle: int):
    #上传图片
    first_upload_btn = "div.reference-upload-eclumn.reference-KpBKPw.light-i454GW[style*='--rotate: -8deg']"
    upload_target = await page.query_selector(first_upload_btn)
    file_input = await upload_target.query_selector("input[type='file']")
    await file_input.set_input_files(first_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", file_input)
    print(f"✅ 首帧图片已上传：{first_path}")

    tail_upload_btn = "div.reference-upload-eclumn.reference-KpBKPw.light-i454GW[style*='--rotate: 5deg']"
    tail_target = await page.query_selector(tail_upload_btn)
    tail_input = await tail_target.query_selector("input[type='file']")
    await tail_input.set_input_files(tail_path)
    await page.evaluate("(el) => el.dispatchEvent(new Event('change', { bubbles: true }))", tail_input)
    print(f"✅ 尾帧图片已上传：{tail_path}")

    # 上传prompt
    await page.fill("textarea.lv-textarea.prompt-textarea-XfqAoB", user_prompt)
    print("✅ prompt 已填写")

    # 根据 cycle 决定提交流程
    # Cycle == 1: 使用原始流程（点击 submit-button-VW0U_J，然后点击确认的“生成”）
    # Cycle >= 2: 使用你指定的第二类按钮 button.submit-button-M82Oxj
    if cycle == 1:
        primary_submit_selector = "button.submit-button-VW0U_J"
        await page.click(primary_submit_selector)
        await asyncio.sleep(0.8)
        # 更可靠地触发 “生成” 按钮（替换原来的 await page.click(...)）
        locator = page.locator("div.content-wt4FUb:has-text('生成')")
        await locator.wait_for(state="visible", timeout=60000)
        await locator.scroll_into_view_if_needed()
        # 触发悬浮样式
        await locator.hover()
        await asyncio.sleep(0.12)

        box = await locator.bounding_box()
        if box:
            center_x = box["x"] + box["width"] / 2
            center_y = box["y"] + box["height"] / 2
            # 物理移动并点击，避免仅调用 click() 无法触发的问题
            await page.mouse.move(center_x, center_y)
            await asyncio.sleep(0.05)
            await page.mouse.click(center_x, center_y)
        else:
            # 退回到普通的 click（极少出现）
            await locator.click()
  
    else:
        second_submit_btn_selector = "button.submit-button-M82Oxj"
        await page.click(second_submit_btn_selector)


    print("✅ 已提交，开始生成视频（等待检测新视频）")

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
            print("✅ 返回新视频链接")
            return new_urls[-1]
        if seconds_elapsed % 2 == 0:
            print(f"⏳ 已等待 {seconds_elapsed} 秒，尚未检测到新视频...")
        if seconds_elapsed >= MAX_WAIT_SECONDS:
            raise Exception(f"超时未检测到新视频（已等待 {MAX_WAIT_SECONDS} 秒）")


# 封装函数
async def generate_videos(photos, prompts):
    pairs = []
    i = 0
    while i + 1 < len(photos):
        pairs.append((photos[i], photos[i + 1]))
        i += 2

    if len(pairs) == 0:
        raise ValueError("无法从 photos 中生成任何配对（需要偶数张，至少 2 张）")

    saved_paths = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 初次登录并切换到视频生成模式
        await initial_setup(page)
        cycle = 1
        for idx, (first_path, tail_path) in enumerate(pairs, start=1):

            # prompt 匹配
            prompt_idx = idx - 1
            if prompt_idx < len(prompts):
                user_prompt = prompts[prompt_idx]
            else:
                user_prompt = prompts[-1]

            print(f"\n=== 开始第 {idx} 个生成任务（{first_path} -> {tail_path}），cycle = {cycle} prompt: {user_prompt} ===")
            video_url = await upload_submit_and_wait(page, first_path, tail_path, user_prompt, cycle)

            if cycle == 1:
                save_name = OUTPUT_FILENAME
            else:
                name, ext = os.path.splitext(OUTPUT_FILENAME)
                save_name = f"{name}_{cycle}{ext}"
            save_path = os.path.join(OUTPUT_DIR, save_name)

            async with aiohttp.ClientSession() as session:
                await download_file(session, video_url, save_path)

            saved_paths.append(save_path)

            # 若有后续任务，重新准备页面继续
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

    print("\n✅ 所有视频已生成并下载完成")
    return saved_paths


# 运行示例
if __name__ == "__main__":
    photo_path = r"C:\Users\Administrator\Desktop\1.jpg"
    photos = [photo_path, photo_path, photo_path, photo_path] 
    prompts = [
        "他们开心地大跳起来",
        "他们相互拥抱"
    ]

    saved = asyncio.run(generate_videos(photos, prompts))
    print("\n已保存文件：")
    for p in saved:
        print(p)
