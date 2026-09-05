# -*- coding: utf-8 -*-
"""優先從 IEEE Xplore 存檔 HTML 的圖片資料夾（*_files/）匯入論文圖到 <out_dir>/img/。

用法：
  python import_html_figures.py "<out_dir>"      # out_dir 傳 paperfolder\\Claude

行為：
  1. 在 out_dir 找 *.html 與其同名 *_files 資產資料夾。
  2. 解析 HTML 的 <img class="document-ft-image" ... alt="Fig. N. - ..." src=".../keelN.gif">：
     - 由 alt 取 Fig 編號（或 Table）；由 src 取本地檔名。
     - 同一圖常有灰階印刷版 + 彩色網頁版兩變體，**優先取彩色版**（同圖兩版時較大 byte 反而常是灰階），皆灰階才比 byte 大小。
  3. 轉存為 img/figNN.png、img/tableN.png（用 PIL 轉 PNG）。
  4. 寫 figures.json（每筆含 fig 編號、file、來源檔名、status:"html"）與
     coverage.json（per_fig 的 covered_by:"html"，視為確定涵蓋）。

回傳（供 skill 判斷是否需退回 PDF 擷取）：
  - 成功匯入 ≥1 張 → 印 "HTML_FIGURES_OK <n>"，exit 0。
  - 找不到 HTML / *_files / 任何圖 → 印 "NO_HTML_FALLBACK_PDF"，exit 2。
（不依賴 fitz，只需 Pillow；勿用 stdin 管線）"""
import sys, os, re, json, html as _html
from urllib.parse import unquote

try:
    from PIL import Image
except Exception:
    Image = None


def _colorfulness(path):
    """回傳影像的平均彩度（每像素 max(r,g,b)-min(r,g,b) 平均）；灰階≈0。只用 PIL。
    IEEE 存檔同一圖常有兩個變體：較大 byte 的是灰階印刷版，較小的反而是彩色網頁版，
    故選圖時以彩度為主鍵，才不會挑到黑白版。"""
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((96, 96))                 # 降採樣加速
        data = im.tobytes()
        n = len(data) // 3
        if n == 0:
            return 0.0
        tot = 0
        for i in range(0, n * 3, 3):
            r, g, b = data[i], data[i + 1], data[i + 2]
            tot += max(r, g, b) - min(r, g, b)
        return tot / n
    except Exception:
        return 0.0

# IEEE Xplore 正文圖片：class 含 document-ft-image，alt 形如 "Fig.\xa0N. - ..." 或 "Table - ..."
_IMG = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
_ATTR = lambda tag, name: (re.search(r'%s\s*=\s*"([^"]*)"' % name, tag, re.IGNORECASE)
                           or re.search(r"%s\s*=\s*'([^']*)'" % name, tag, re.IGNORECASE))
_FIG_ALT = re.compile(r'Fig(?:ure)?\.?\s*(\d+)', re.IGNORECASE)
_TBL_ALT = re.compile(r'\bTable\b\s*(\d*)', re.IGNORECASE)
_RASTER = (".gif", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")


def _find_html_and_files(out_dir):
    htmls = [f for f in os.listdir(out_dir) if f.lower().endswith(".html")]
    for h in htmls:
        base = h[:-5]
        cand = os.path.join(out_dir, base + "_files")
        if os.path.isdir(cand):
            return os.path.join(out_dir, h), cand
    # 退路：任何 *_files 資料夾
    for f in os.listdir(out_dir):
        if f.endswith("_files") and os.path.isdir(os.path.join(out_dir, f)):
            return (os.path.join(out_dir, htmls[0]) if htmls else None,
                    os.path.join(out_dir, f))
    return (os.path.join(out_dir, htmls[0]) if htmls else None, None)


def import_html(out_dir):
    fig_dir = os.path.join(out_dir, "img")
    html_path, files_dir = _find_html_and_files(out_dir)
    if not html_path or not files_dir:
        print("NO_HTML_FALLBACK_PDF")
        return 2
    if Image is None:
        print("NO_HTML_FALLBACK_PDF  (Pillow 未安裝)")
        return 2

    txt = open(html_path, encoding="utf-8", errors="replace").read()

    # key -> list of (abs_path, size)；key 為 "fig<N>" 或 "table<N|序>"
    groups, tbl_auto = {}, 0
    for tag in _IMG.findall(txt):
        cls = _ATTR(tag, "class")
        alt = _ATTR(tag, "alt")
        src = _ATTR(tag, "src")
        if not src:
            continue
        alt_v = _html.unescape(alt.group(1)) if alt else ""
        cls_v = cls.group(1) if cls else ""
        is_ft = "document-ft-image" in cls_v
        # 取本地檔名
        fname = unquote(os.path.basename(_html.unescape(src.group(1)).split("?")[0]))
        if os.path.splitext(fname)[1].lower() not in _RASTER:
            continue
        local = os.path.join(files_dir, fname)
        if not os.path.isfile(local):
            continue
        # 判斷是 Fig 或 Table（優先用 alt；ft-image 才採信無 alt 的情形）
        mf = _FIG_ALT.search(alt_v)
        mt = _TBL_ALT.search(alt_v)
        if mf:
            key = "fig%d" % int(mf.group(1))
        elif mt:
            if mt.group(1):
                key = "table%d" % int(mt.group(1))
            else:
                tbl_auto += 1
                key = "table%d" % tbl_auto
        elif is_ft:
            # 無法判定編號的正文圖，略過（避免污染）
            continue
        else:
            continue
        groups.setdefault(key, []).append(local)

    if not groups:
        print("NO_HTML_FALLBACK_PDF  (HTML 內未找到可辨識的圖)")
        return 2

    os.makedirs(fig_dir, exist_ok=True)
    manifest, fig_nums = [], []
    for key, lst in groups.items():
        lst = list(dict.fromkeys(lst))                  # 去重
        if len(lst) == 1:
            src_path = lst[0]
        else:                                           # 多變體：優先彩色，再比 byte 大小
            src_path = max(lst, key=lambda p: (round(_colorfulness(p), 1),
                                               os.path.getsize(p)))
        if key.startswith("fig"):
            n = int(key[3:]); out_name = "fig%02d.png" % n; fig_nums.append(n)
        else:
            n = int(key[5:]); out_name = "table%d.png" % n
        out_path = os.path.join(fig_dir, out_name)
        Image.open(src_path).convert("RGB").save(out_path)
        manifest.append({"file": "img/%s" % out_name, "source": os.path.basename(src_path),
                         "kind": "table" if key.startswith("table") else "figure",
                         "num": n, "status": "html"})

    fig_nums = sorted(set(fig_nums))
    per_fig = [{"fig": n, "covered_by": "html",
                "file": "img/fig%02d.png" % n} for n in fig_nums]
    coverage = {"source": "html", "figs_detected": fig_nums,
                "total_figs": len(fig_nums), "rendered_pages": [], "per_fig": per_fig}
    with open(os.path.join(fig_dir, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False, indent=2)
    manifest.sort(key=lambda m: (m["kind"], m["num"]))
    with open(os.path.join(fig_dir, "figures.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    ntab = sum(1 for m in manifest if m["kind"] == "table")
    print("Imported from HTML: %d figures + %d tables -> %s" % (len(fig_nums), ntab, fig_dir))
    print("Figs:", fig_nums)
    print("HTML_FIGURES_OK %d" % len(fig_nums))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python import_html_figures.py \"<paperfolder>\\Claude\"")
        sys.exit(1)
    sys.exit(import_html(sys.argv[1]))
