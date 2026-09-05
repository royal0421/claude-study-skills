# -*- coding: utf-8 -*-
"""
extract_chapter.py — book-to-study Phase 1 擷取腳本（v1.0, 2026-07-07）

用法（路徑一律絕對路徑，含中文路徑要加引號）：
  python extract_chapter.py "<章節PDF>" "<整本書PDF或NONE>" "<AI資料夾>" [章號]

  參數 1：單章 PDF（如 Ch2.pdf）
  參數 2：整本書 PDF（供 toc 章節結構；找不到書時填字面值 NONE）
  參數 3：輸出資料夾（章節資料夾下的 AI\，不存在會自動建立）
  參數 4：章號（選填；省略時從 PDF 第 1 頁 "Chapter N" 自動偵測，
          偵測失敗再退回資料夾名 "ChN ..." 推斷）

輸出（全部在 <AI資料夾> 下）：
  _extracted.txt              全文文字，每頁前有 [Page N] 標記
  outline.json                本章節結構＋全書章標題表（schema 見 SKILL.md）
  sections/sec_<N.X>.txt      按大節（N.X）切分的文字檔；章首散文存 sec_<N>_head.txt
  figures/fig{N}-{MM}.png     版面剪裁算繪的原書圖（MM = Fig 編號兩位補零，如 fig2-05.png；
                              帶字母尾碼的圖說如 "Fig 2.5a" 歸入主編號 2.5）
  figures/page_{P}.png        整頁 300 DPI 算繪（剪裁異常時的兜底）
  figures.json                圖片 manifest（schema 見 SKILL.md）

哨兵字串與 exit code：
  "EXTRACT OK pages=.. sections=..(sliced=..) figs_detected=.. clipped=.. rendered_pages=.. missing=[..] unsliced=[..]"
      → exit 0。注意：missing 非空仍 exit 0（擷取流程完成，但有圖沒著落，
        由呼叫端讀 figures.json 處理）。exit 0 不代表所有圖都齊。
  "SCAN_PDF_NO_TEXT_LAYER"    → exit 1（前 3 頁文字合計 <500 字元＝掃描版）
  "CHAPTER_NUM_NOT_FOUND"     → exit 1（無法偵測章號且未給參數 4）
  "BOOK_TOC_EMPTY_FALLBACK_REGEX" → 非致命警告行（書 toc 沒本章條目，改用內文 regex）
  其他未攔截錯誤 → Python traceback, exit 非 0

覆寫行為（冪等）：重跑會覆寫 _extracted.txt / outline.json / figures.json，
  清空 sections/*.txt，刪除 figures/ 內既有的 fig{本章號}-*.png 與 page_*.png 後重抽。
  絕不動 figures/ 內的 aux-*.png 與其他任何檔案（自繪圖安全）。
"""
import sys
import re
import json
from pathlib import Path

import fitz  # PyMuPDF


def clean_toc_title(t):
    # 書 toc 標題含 \xa0 與私用區雜訊字元（2026-07-07 對本書實測）；標題為英文，僅保留可印 ASCII
    t = ''.join(ch if 0x20 <= ord(ch) <= 0x7E else ' ' for ch in t)
    return re.sub(r'\s+', ' ', t).strip()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    ch_pdf = Path(sys.argv[1])
    book_pdf_arg = sys.argv[2]
    ai_dir = Path(sys.argv[3])
    ch_override = sys.argv[4] if len(sys.argv) > 4 else None

    doc = fitz.open(str(ch_pdf))
    npages = doc.page_count
    pages_text = [doc[i].get_text() for i in range(npages)]

    # --- 掃描版偵測 ---
    if sum(len(t) for t in pages_text[:3]) < 500:
        print("SCAN_PDF_NO_TEXT_LAYER")
        sys.exit(1)

    # --- 章號 ---
    chap = None
    if ch_override:
        chap = int(ch_override)
    else:
        m = re.search(r'Chapter\s+(\d+)', pages_text[0])
        if m:
            chap = int(m.group(1))
        else:
            m2 = re.match(r'Ch(?:apter)?\s*(\d+)', ch_pdf.parent.name)
            if m2:
                chap = int(m2.group(1))
    if chap is None:
        print("CHAPTER_NUM_NOT_FOUND")
        sys.exit(1)

    # --- 目錄結構與清理（只清自產物，aux-* 不動）---
    ai_dir.mkdir(exist_ok=True)
    figdir = ai_dir / "figures"
    figdir.mkdir(exist_ok=True)
    secdir = ai_dir / "sections"
    secdir.mkdir(exist_ok=True)
    for f in secdir.glob("*.txt"):
        f.unlink()
    for f in list(figdir.glob(f"fig{chap}-*.png")) + list(figdir.glob("page_*.png")):
        f.unlink()

    # --- _extracted.txt ---
    (ai_dir / "_extracted.txt").write_text(
        "\n\n".join(f"[Page {i+1}]\n{t}" for i, t in enumerate(pages_text)),
        encoding="utf-8")

    # --- outline：書 toc 優先，退路 regex ---
    sections = []       # 本章全部條目（含 N.X 與 N.X.Y）
    book_chapters = []  # 全書章標題（跨章 Chap. N 參照用）
    chap_base_page = None  # 本章在書中的起始頁（book page → 章節 pdf page 換算）
    if book_pdf_arg.upper() != "NONE" and Path(book_pdf_arg).exists():
        bdoc = fitz.open(book_pdf_arg)
        for lvl, title, pg in bdoc.get_toc():
            t = clean_toc_title(title)
            m1 = re.match(r'(\d+)\s+(.+)', t)
            if lvl == 1 and m1:
                book_chapters.append({"chapter": int(m1.group(1)), "title": m1.group(2)})
                if int(m1.group(1)) == chap:
                    chap_base_page = pg
            m2 = re.match(rf'({chap}\.\d+(?:\.\d+)?)\s+(.+)', t)
            if m2:
                pdf_pg = (pg - chap_base_page + 1) if chap_base_page else None
                sections.append({"num": m2.group(1), "title": m2.group(2),
                                 "level": m2.group(1).count('.') + 1, "pdf_page": pdf_pg})
        bdoc.close()
    if not sections:
        print("BOOK_TOC_EMPTY_FALLBACK_REGEX")
        seen = set()
        for i, t in enumerate(pages_text):
            for mm in re.finditer(rf'^({chap}\.\d+(?:\.\d+)?)\s+(\S[^\n]*)$', t, re.M):
                num = mm.group(1)
                if num not in seen:
                    seen.add(num)
                    sections.append({"num": num, "title": mm.group(2).strip(),
                                     "level": num.count('.') + 1, "pdf_page": i + 1})
    sections.sort(key=lambda s: [int(x) for x in s["num"].split('.')])

    (ai_dir / "outline.json").write_text(
        json.dumps({"chapter": chap, "sections": sections, "book_chapters": book_chapters},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # --- 切大節（level==2 的 N.X）：先在全文精確定位標題，失敗退頁界 ---
    full = "\n".join(pages_text)  # 無頁標記版本，供定位與切分
    majors = [s for s in sections if s["level"] == 2]
    positions = []
    for s in majors:
        # 標題詞前 3 個字（避免整串標題因換行/連字對不上）
        words = re.escape(' '.join(s["title"].split()[:3]))
        pat = re.compile(rf'^{re.escape(s["num"])}\s+{words}'.replace(r'\ ', r'\s+'), re.M)
        m = pat.search(full)
        if not m:
            pat = re.compile(rf'^{re.escape(s["num"])}\s+\S', re.M)
            m = pat.search(full)
        positions.append(m.start() if m else None)
    # 頁界退路：位置缺的用 pdf_page 換算字元偏移
    page_offsets = []
    off = 0
    for t in pages_text:
        page_offsets.append(off)
        off += len(t) + 1  # join 的 \n
    for i, s in enumerate(majors):
        if positions[i] is None and s.get("pdf_page"):
            positions[i] = page_offsets[min(s["pdf_page"], npages) - 1]
    # 章首散文（第一節之前）
    known = [(p, s) for p, s in zip(positions, majors) if p is not None]
    known.sort(key=lambda x: x[0])
    if known and known[0][0] > 0:
        (secdir / f"sec_{chap}_head.txt").write_text(full[:known[0][0]], encoding="utf-8")
    for idx, (p, s) in enumerate(known):
        end = known[idx + 1][0] if idx + 1 < len(known) else len(full)
        (secdir / f"sec_{s['num']}.txt").write_text(full[p:end], encoding="utf-8")
    unsliced = [s["num"] for p, s in zip(positions, majors) if p is None]

    # --- 圖片：圖說定位 → 版面剪裁算繪（向量圖/點陣圖通吃）---
    # 原理：Springer 版式圖說位於圖的下方。對每個圖說，收集「上一個圖說底部～本圖說頂部」
    # 區間內的繪圖元素（向量 drawings＋點陣 image blocks），取聯集 bbox 剪裁、2x 算繪。
    # 聯集異常（高度 >500pt 疑似誤聯、<15pt 空殼）→ 該圖退整頁 300 DPI 算繪兜底。
    fig_items = []
    detected = []  # [(fig_num_int, page)]
    cap_re = re.compile(rf'^(?:Fig|Figure)\.?\s*{chap}\.(\d+)[a-z]?\b')  # 字母尾碼（Fig 2.5a）歸入主編號
    for i in range(npages):
        page = doc[i]
        pdict = page.get_text("dict")
        captions = []  # (fnum, bbox)
        for blk in pdict["blocks"]:
            if blk.get("type") != 0 or not blk.get("lines"):
                continue
            line0 = "".join(sp.get("text", "") for sp in blk["lines"][0].get("spans", []))
            m = cap_re.match(line0.strip())
            if m:
                fnum = int(m.group(1))
                if not any(d[0] == fnum for d in detected):
                    captions.append((fnum, fitz.Rect(blk["bbox"])))
                    detected.append((fnum, i + 1))
        if not captions:
            continue
        captions.sort(key=lambda c: c[1].y0)
        elems = []
        for d in page.get_drawings():
            r = fitz.Rect(d["rect"])
            if r.height < 3 and r.width > 300:   # 橫貫版心的頁眉/頁腳分隔線
                continue
            if r.width < 2 and r.height < 2:     # 髮絲點
                continue
            elems.append(r)                       # 曲線圖由大量小線段組成，勿按尺寸過濾
        for blk in pdict["blocks"]:
            if blk.get("type") == 1:
                r = fitz.Rect(blk["bbox"])
                if r.width >= 20 and r.height >= 20:
                    elems.append(r)
        prev_bottom = 0.0
        content_bot = page.rect.height - 36  # 頁腳緩衝
        for k, (fnum, cbox) in enumerate(captions):
            # Springer margin-caption 版式（本書實測）：圖說在左側邊欄、圖主體在其右側
            # 同高並向下延伸 → 圖區帶 = [本圖說頂, 下一圖說頂)（最後一張到內容底）
            y_bot = captions[k + 1][1].y0 - 6 if k + 1 < len(captions) else content_bot
            members = [r for r in elems if cbox.y0 - 4 < (r.y0 + r.y1) / 2 < y_bot]
            if not members:
                # 退階：傳統「圖在圖說上方」版式
                members = [r for r in elems if prev_bottom < (r.y0 + r.y1) / 2 < cbox.y0]
            prev_bottom = cbox.y1
            fn = f"fig{chap}-{fnum:02d}.png"
            done = False
            if members:
                u = members[0]
                for r in members[1:]:
                    u = u | r
                u = fitz.Rect(u.x0 - 4, u.y0 - 4, u.x1 + 4, min(u.y1 + 4, y_bot)) & page.rect
                if 15 <= u.height <= 500:
                    page.get_pixmap(clip=u, matrix=fitz.Matrix(2, 2)).save(str(figdir / fn))
                    fig_items.append({"fig": f"{chap}.{fnum}", "page": i + 1,
                                      "file": fn, "status": "clipped"})
                    done = True
            if not done:
                pfn = f"page_{i+1}.png"
                if not (figdir / pfn).exists():
                    page.get_pixmap(dpi=300).save(str(figdir / pfn))
                fig_items.append({"fig": f"{chap}.{fnum}", "page": i + 1,
                                  "file": pfn, "status": "rendered_page"})

    covered = {it["fig"] for it in fig_items}
    missing = [f"{chap}.{f}" for f, _ in detected if f"{chap}.{f}" not in covered]
    (ai_dir / "figures.json").write_text(
        json.dumps({"chapter": chap,
                    "figs_detected": [f"{chap}.{f}" for f, _ in sorted(detected)],
                    "items": fig_items, "missing": missing,
                    "unsliced_sections": unsliced},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    clip = sum(1 for it in fig_items if it["status"] == "clipped")
    ren = len({it["file"] for it in fig_items if it["status"] == "rendered_page"})
    print(f"EXTRACT OK pages={npages} sections={len(majors)}(sliced={len(known)}) "
          f"figs_detected={len(detected)} clipped={clip} rendered_pages={ren} "
          f"missing={missing} unsliced={unsliced}")
    doc.close()


if __name__ == "__main__":
    main()
