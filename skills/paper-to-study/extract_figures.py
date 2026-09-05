# -*- coding: utf-8 -*-
"""抽 PDF 內嵌圖到 <out_dir>/img/ 並寫 figures.json + coverage.json；亦可算繪指定頁面。
用法：
  python extract_figures.py "<pdf>" "<out_dir>"            # 抽內嵌圖 + 保證每個 Fig 編號都對應到影像
  python extract_figures.py "<pdf>" "<out_dir>" page <N>   # 算繪第 N 頁為 img/page_N.png
（out_dir 傳 Claude/；勿用 stdin 管線）

保證機制（以「每個 Fig 編號是否對應到影像」判斷）：
  抽完內嵌點陣圖後，掃描各頁「Fig. N / Figure N」圖說建立 {Fig 編號 → 頁碼}。
  以「該頁的 圖說+表說 總數」對「該頁抽到的內嵌圖數」做比較（表也佔影像名額，
  故能連帶抓出躲在表圖後面的向量圖）；任一 Fig 所在頁影像不足，就把該頁 300 DPI
  算繪成 page_N.png 補上。最後輸出 coverage.json：每個 Fig 編號的 頁碼 + 涵蓋來源，
  供 skill 做「逐 Fig」覆蓋率確認（embedded 候選需由 Claude 視覺對應最終確認；
  rendered_page 則為向量圖後備）。判定方向安全：誤判只會多算繪一頁，不會漏掉 Fig。"""
import sys, os, json, re, fitz

# 圖說行：行首 Fig/Figure + 數字 + 分隔符，或 數字 + 空白 + 大寫字母（標題）；排除內文引用「Fig. 1 shows」
_CAP_FIG = re.compile(r'(?mi)^\s*Fig(?:ure)?\.?\s*(\d+)\s*[:.‐-―]|^\s*Fig(?:ure)?\.?\s*(\d+)\s+[A-Z]')
_CAP_TBL = re.compile(r'(?mi)^\s*Tab(?:le)?\.?\s*(\d+)\s*[:.‐-―]|^\s*Tab(?:le)?\.?\s*(\d+)\s+[A-Z]')

def _caps_per_page(doc, pat):
    """回傳 {page_index(0-based): set(編號)}，只計圖說/表說行、不計內文引用。"""
    out = {}
    for pno in range(len(doc)):
        nums = {int(a or b) for a, b in pat.findall(doc[pno].get_text())}
        if nums:
            out[pno] = nums
    return out

def render_page(pdf_path, out_dir, page_no):
    """算繪第 page_no 頁（1-based）為高解析 PNG，保留向量圖原貌。"""
    fig_dir = os.path.join(out_dir, "img")
    os.makedirs(fig_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    pm = doc[page_no - 1].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
    out = os.path.join(fig_dir, f"page_{page_no}.png")
    pm.save(out)
    print(f"Rendered page {page_no} -> {out}")
    return out, pm.width, pm.height

def extract(pdf_path, out_dir):
    fig_dir = os.path.join(out_dir, "img")
    os.makedirs(fig_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    manifest, idx, seen = [], 0, set()
    saved_per_page = {}                       # page_index(0-based) -> 已存內嵌圖數
    for pno in range(len(doc)):
        for img in doc.get_page_images(pno):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue
            if pix.n >= 5:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if pix.width < 150 or pix.height < 150:
                continue
            idx += 1
            fn = f"fig_{idx:02d}.png"
            pix.save(os.path.join(fig_dir, fn))
            saved_per_page[pno] = saved_per_page.get(pno, 0) + 1
            manifest.append({"file": f"img/{fn}", "page": pno + 1,
                             "width": pix.width, "height": pix.height,
                             "area": pix.width * pix.height, "status": "ok"})

    # ── 建立 Fig/Table → 頁 對應 ──
    fig_pages = _caps_per_page(doc, _CAP_FIG)        # {pno: set(Fig N)}
    tbl_pages = _caps_per_page(doc, _CAP_TBL)        # {pno: set(Table N)}
    fig_to_page = {}
    for pno, nums in fig_pages.items():
        for n in nums:
            fig_to_page.setdefault(n, pno + 1)        # 首次出現的頁（1-based）
    all_figs = sorted(fig_to_page)

    # ── 逐 Fig 判斷覆蓋：該頁 (圖說+表說) 總數 > 該頁內嵌圖數 → 算繪該頁補上 ──
    rendered_pages = set()
    for pno in sorted(set(fig_pages) | set(tbl_pages)):
        need = len(fig_pages.get(pno, set())) + len(tbl_pages.get(pno, set()))
        have = saved_per_page.get(pno, 0)
        if need > have and (pno + 1) not in rendered_pages:
            out, w, h = render_page(pdf_path, out_dir, pno + 1)
            manifest.append({"file": f"img/page_{pno + 1}.png", "page": pno + 1,
                             "width": w, "height": h, "area": w * h,
                             "status": "rendered_page",
                             "figs": sorted(fig_pages.get(pno, set())),
                             "note": "整頁算繪補上（該頁圖說+表說數 > 內嵌圖數，疑有向量圖）"})
            rendered_pages.add(pno + 1)

    # ── coverage.json：逐 Fig 編號 → 頁碼 + 涵蓋來源 ──
    per_fig = []
    for n in all_figs:
        pg = fig_to_page[n]
        if pg in rendered_pages:
            src = "rendered_page"                       # 向量圖後備，確定有影像
        else:
            src = "embedded_candidate"                  # 該頁有足夠內嵌圖，待 Claude 視覺對應確認
        per_fig.append({"fig": n, "page": pg, "covered_by": src})
    coverage = {"figs_detected": all_figs, "total_figs": len(all_figs),
                "rendered_pages": sorted(rendered_pages), "per_fig": per_fig}
    with open(os.path.join(fig_dir, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False, indent=2)

    manifest.sort(key=lambda m: m["area"], reverse=True)
    with open(os.path.join(fig_dir, "figures.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    n_ok = sum(1 for m in manifest if m["status"] == "ok")
    print(f"Extracted {n_ok} embedded figures -> {fig_dir}")
    if all_figs:
        print(f"Caption Figs detected: {all_figs} (total {len(all_figs)})")
    if rendered_pages:
        rf = sorted({n for n in all_figs if fig_to_page[n] in rendered_pages})
        print(f"Coverage fallback: rendered pages {sorted(rendered_pages)} → 補上 Fig {rf}")
    print("Per-Fig coverage written -> coverage.json"
          + ("（仍有 embedded_candidate，需 Claude 逐 Fig 視覺對應確認）" if any(
              p['covered_by'] == 'embedded_candidate' for p in per_fig) else ""))

if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[3] == "page":
        render_page(sys.argv[1], sys.argv[2], int(sys.argv[4]))
    else:
        extract(sys.argv[1], sys.argv[2])
