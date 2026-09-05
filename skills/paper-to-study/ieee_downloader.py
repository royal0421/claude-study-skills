import asyncio
import json
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

_stealth = Stealth()

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "https://ieeexplore.ieee.org"

_PREFLIGHT_ARTICLE = "https://ieeexplore.ieee.org/document/1253881/"
_PREFLIGHT_STAMP   = f"{BASE_URL}/stamp/stamp.jsp?tp=&arnumber=1253881"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def sanitize(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', name).strip()
    return cleaned[:100]


def stamp_url_from(article_url: str) -> str:
    """
    從 IEEE Xplore 文章 URL 直接解出 stamp.jsp URL。
    例：https://ieeexplore.ieee.org/document/1253881/
      → https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=1253881
    """
    m = re.search(r'/document/(\d+)', article_url)
    if not m:
        raise ValueError(f"無法從 URL 解析 arnumber：{article_url}")
    return f"{BASE_URL}/stamp/stamp.jsp?tp=&arnumber={m.group(1)}"


async def new_stealth_page(context):
    page = await context.new_page()
    await _stealth.apply_stealth_async(page)
    return page


async def fetch_pdf_bytes(context, stamp_url: str, referer: str) -> bytes:
    """
    監聽所有 network response，攔截 content-type=pdf 的回應取得 bytes。
    讓瀏覽器自己完整執行 Incapsula JS 挑戰後取得真正的 PDF。
    """
    page = await new_stealth_page(context)
    captured: list[bytes] = []
    done = asyncio.Event()

    async def on_response(resp):
        ct = resp.headers.get("content-type", "")
        if "pdf" in ct.lower() and not done.is_set():
            try:
                body = await resp.body()
                if body[:4] == b"%PDF":
                    captured.append(body)
                    done.set()
            except Exception:
                pass

    page.on("response", on_response)
    await page.set_extra_http_headers({"Referer": referer})

    try:
        await page.goto(stamp_url, wait_until="networkidle", timeout=60000)
    except Exception:
        pass  # PDF viewer 保持連線可能導致 networkidle timeout，忽略

    # 額外等 5 秒讓 PDF response 進來
    try:
        await asyncio.wait_for(done.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        pass

    await page.close()

    if captured:
        return captured[0]
    raise ValueError("未能擷取 PDF response，請確認 VPN 已連線")


async def check_institutional_access(context) -> bool:
    """
    預檢：先讓 stealth 頁面通過文章頁的 Incapsula 挑戰，
    再嘗試抓取 stamp.jsp 的 PDF bytes。
    """
    page = await new_stealth_page(context)
    try:
        await page.goto(_PREFLIGHT_ARTICLE, wait_until="networkidle", timeout=40000)
    except Exception:
        pass  # networkidle 可能 timeout，但 Incapsula challenge 仍在背景執行
    finally:
        await page.close()

    try:
        body = await fetch_pdf_bytes(context, _PREFLIGHT_STAMP, _PREFLIGHT_ARTICLE)
        return body[:4] == b"%PDF"
    except Exception as e:
        print(f"  [debug] 預檢失敗：{e}")
        return False


async def download_paper(context, ref: str, title: str, url: str, download_dir: Path) -> dict:
    """
    直接從文章 URL 解出 arnumber → 建 stamp URL → 下載 PDF。
    不需要瀏覽文章頁去找按鈕（預檢已建立 Incapsula session）。
    """
    print(f"  -> [{ref}] {title[:60]}...")
    try:
        stamp_url = stamp_url_from(url)
        pdf_bytes = await fetch_pdf_bytes(context, stamp_url, url)

        filename = f"[{ref}]_{sanitize(title)}.pdf"
        save_path = download_dir / filename
        save_path.write_bytes(pdf_bytes)
        size_kb = round(len(pdf_bytes) / 1024)
        print(f"  [OK] {filename}（{size_kb} KB）")
        return {"ref": ref, "status": "ok", "file": filename}

    except Exception as e:
        print(f"  [FAIL] [{ref}] 失敗：{e}")
        return {"ref": ref, "status": "error", "error": str(e)}


async def run(input_path: str, download_dir: Path):
    papers = json.loads(Path(input_path).read_text(encoding="utf-8"))
    download_dir.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄：{download_dir}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=_USER_AGENT,
            accept_downloads=True,
        )

        # ── VPN / 機構訂閱預檢 ───────────────────────────────────
        print("正在確認機構訂閱存取權限...")
        if not await check_institutional_access(context):
            await browser.close()
            print()
            print("[WARNING] 無法取得 IEEE 全文 PDF。")
            print("          請先連接學校 VPN，再重新執行腳本。")
            sys.exit(1)
        print("[OK] 機構訂閱確認，開始下載...\n")
        # ─────────────────────────────────────────────────────────

        results = []
        for paper in papers:
            result = await download_paper(
                context,
                paper["ref"],
                paper["title"],
                paper["url"],
                download_dir,
            )
            results.append(result)
        await browser.close()

    ok_list   = [r for r in results if r["status"] == "ok"]
    fail_list = [r for r in results if r["status"] == "error"]
    print(f"\n===== 下載結果 =====")
    print(f"成功：{len(ok_list)} 篇　失敗：{len(fail_list)} 篇")
    if fail_list:
        print("\n失敗清單：")
        for r in fail_list:
            print(f"  [FAIL] [{r['ref']}]：{r['error']}")


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "ieee_papers.json"
    # sys.argv[2]：自訂輸出目錄；未提供時預設為 <HOME>\Downloads
    download_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"<HOME>\Downloads")
    asyncio.run(run(input_file, download_dir))
