---
name: paper-to-ppt
description: 將 IEEE 論文（HTML + 根層論文 PDF）轉成學術風格 PPTX，使用 slides.pptx 模板（三層尋找：論文根層 → Claude/ → skill 資料夾 canonical；皆無則中止）。投影片圖片一律取自論文 PDF 擷取（PyMuPDF）：Claude/img/ 已有 PDF 來源擷取（figures.json 含 status:"ok"）就重用，否則執行擷取（HTML 來源的 figures.json 視同未擷取）。HTML 僅供章節結構、圖說與 metadata。模板幾何常數、字型規則、Wingdings 子彈格式已完整寫在本檔內文。
---

# Paper-to-PPT Skill

將 IEEE 論文（HTML + 根層 PDF）轉成學術 PPTX，**全程自動**——不需要問使用者哪些圖要放、怎麼分、說明怎麼寫。生成後使用者自行用 QA 匯出的 JPEG 做最後確認。

## 呼叫方式

```
/paper-to-ppt <html_path> <pdf_path> [slides_template_path]
```

- `html_path`：Ctrl+S 存檔的 `.html`
- `pdf_path`：論文 PDF（必填，用於偵測圖對關係與分析 Conclusion）
- `slides_template_path`：選填；若省略，依序尋找（與程式碼一致的三層順序）：
  1. 論文根層（pdf 同層）的 `slides.pptx`（per-paper copy）
  2. `Claude\slides.pptx`
  3. `<SKILLS_ROOT>\paper-to-ppt\slides.pptx`（canonical）

  **三處皆無 → 中止並回報使用者**。模板是必需檔：腳本要開它取 Title／Outline／Thanks 頁與版型，幾何常數雖已寫在本檔，仍**無法**無模板產出。

## 套件需求

`python-pptx`、`lxml`、`pypdf`（Phase 2a 讀 PDF 文字）、`PyMuPDF`（extract_figures.py）、`beautifulsoup4`（Phase 1 解析 HTML）、`Pillow`（圖片等比縮放；缺了退化成 bounding-box 塞圖，會變形）。缺 → `pip install <名>` 重試一次 → 仍缺回報使用者。

---

## ⚠️ Critical Pitfalls（必讀，這兩個錯誤無聲失敗）

### 1. BULLET_CHAR — 永遠使用 Python escape，不可貼入原義字符

```python
# ✅ 正確：Python escape notation（存檔不會遺失）
BULLET_CHAR = "\uF06C"   # Wingdings U+F06C large ●

# ❌ 危險：貼入原義字符（編輯器/git 會靜默丟棄，腳本跑完無 ●）
BULLET_CHAR = ""         # 此字符在多數編輯器中不可見，容易被靜默刪除
```

**症狀**：Conclusion 與 desc 的子彈消失，整張 slide 看起來沒有 ●。  
**確認方式**（寫成 `Claude\check_bullet.py` 再執行——不要用 `python -c` 單行式，PowerShell 5.1 會吃掉引號）：
```python
content = open(r"<paperfolder>\Claude\gen_ppt.py", encoding="utf-8").read()
idx = content.find('BULLET_CHAR')
print([hex(ord(c)) for c in content[idx:idx+25]])
# 正確（擇一）：含 '0x5c','0x75','0x46','0x30','0x36','0x43' ＝ escape 寫法 \uF06C（建議形式）
#              或含 '0xf06c' ＝ 原義字元仍在
# 錯誤：引號間空無一物（...'0x22','0x22'...）＝ 子彈已遺失，立即改回 "\uF06C"
```

---

### 2. DESC_H — 不可低於 500000 EMU

```
spcBef(12700) + 2×18pt_line(228600×2=457200) = 469900 EMU
DESC_H = 500000  →  buffer = 30100 EMU，DESC_GAP = 20000 EMU
                    IMG_TOP gap = 50100 EMU ≈ 7px（可見間距）
```

**症狀**：第三行文字溢出進入圖片區域（尤其單圖、圖片頂部有標題列時最明顯）。  
**上限**：每張 slide 的 desc 文字不超過 2 行。  
- 一般混合大小寫：≤ 130 chars  
- 大寫字母密集（IGSS/IDSS、IG-VGS、TD1–TD10 等）：≤ 120 chars（Arial Bold 大寫較寬）

---

## 前置確認

```python
from pathlib import Path
html  = Path(r"<html_path>")          # 僅供章節結構、圖說、metadata
pdf   = Path(r"<pdf_path>")           # 圖片唯一來源：與 Claude/ 同層的論文 PDF
claude_dir = pdf.parent / "Claude"    # 副產物（擷取圖、figures.json）
img_dir    = claude_dir / "img"
out   = pdf.parent / "PPT.pptx"       # 成品輸出至論文資料夾根層；重跑會覆寫，要留舊版先改名

CANONICAL_TPL = Path(r"<SKILLS_ROOT>\paper-to-ppt\slides.pptx")
if slides_template_path:
    tpl = Path(r"<slides_template_path>")
elif (pdf.parent / "slides.pptx").exists():
    tpl = pdf.parent / "slides.pptx"
elif (claude_dir / "slides.pptx").exists():
    tpl = claude_dir / "slides.pptx"
else:
    tpl = CANONICAL_TPL   # always available

for label, p in [("HTML", html), ("PDF", pdf), ("Template", tpl)]:
    print(f"{label:10}: {'OK' if p.exists() else 'MISSING'} → {p}")

if not (html.exists() and pdf.exists() and tpl.exists()):
    raise SystemExit("[STOP] 前置檔案缺失（見上方 MISSING）——補齊後重跑 /paper-to-ppt，不要無檔硬做")
```

> **圖片來源（重要）**：投影片用圖**一律出自根層論文 PDF 的擷取結果**——投影片會全幅放大，PDF 內嵌圖解析度優於 IEEE 網頁 GIF。study/review 可能先用 HTML 匯過圖（那份 figures.json 的 status 全為 `"html"`、檔名 `figNN.png`）——**對 ppt 而言視同未擷取**，照 Phase 1a-2 判準重跑 PDF 擷取。HTML 在本 skill 只用來取圖編號、圖說與章節歸屬。資料夾結構仍與 study/review 共用同一份 `Claude/ + Reference/ + 根層 PDF`。

---

## Phase 1：解析 HTML

### 1a. 建立 fig_map

```python
from bs4 import BeautifulSoup

with open(html, encoding='utf-8', errors='replace') as f:
    soup = BeautifulSoup(f, 'html.parser')

# 只從 HTML 取圖編號與圖說；圖片檔在 1a-2 由 PDF 擷取後填入 path/exists
fig_map = {}  # "fig1" -> {num, caption, path, exists}

for div in soup.find_all('div', class_='figure'):
    fig_id  = div.get('id', '')
    img     = div.find('img')
    caption = div.find(class_='figcaption')
    num_str = ''.join(filter(str.isdigit, fig_id))
    fig_map[fig_id] = {
        'num':     int(num_str) if num_str else 0,
        'caption': caption.get_text(separator=' ', strip=True) if caption else (img.get('alt','') if img else ''),
        'path':    None,    # ← 由 Phase 1a-2 從 PDF 擷取後填入
        'exists':  False,
    }

total_figs = len(fig_map)
print(f"Total figures (from HTML): {total_figs}")
```

**自查點**：`total_figs == 0` → HTML 存檔壞掉或非 IEEE 版面（抓不到 `div.figure`）→ **中止**，請使用者重新 Ctrl+S 完整存檔（先滾到頁尾讓圖片載入）再重跑；不要在 0 圖狀態下繼續生成空殼簡報。

> **Table 處理原則**：本 skill 只自動處理 Fig（`div.figure`），Table **不**自動進投影片。若某張 Table 是核心貢獻（如 benchmark 比較表），由 Claude 判斷後用 page 模式算繪該頁充當圖插入（同 Phase 1c 作法），並在 desc 註明。

### 1a-2. 取得 PDF 擷取圖片（有「PDF 來源」擷取就重用，否則執行擷取）

圖片來源是**根層 PDF**，抽到 `Claude/img/`。`extract_figures.py` 在 study／review 資料夾各有一份 byte-identical 副本，ppt 呼叫 review 那份。**重用判準（機械，2026-07-06 定案）**：`figures.json` 存在**且**內含至少一筆 `status:"ok"`（＝PDF 來源擷取）→ 沿用、跳過擷取；否則（檔案不存在，**或全是 HTML 來源的 `status:"html"`**）→ 執行 PDF 擷取。

```python
import json
from pathlib import Path
img_dir   = pdf.parent / "Claude" / "img"
figs_json = img_dir / "figures.json"

need_extract = True
if figs_json.exists():
    figures = json.loads(figs_json.read_text(encoding="utf-8"))
    ok = [f for f in figures if f.get("status") == "ok"]
    if ok:
        need_extract = False
        print(f"[reuse] 沿用既有 PDF 擷取：{len(ok)} 張 ok 圖，跳過重抽")
    else:
        print("[extract] figures.json 是 HTML 來源（status 全為 html）——ppt 需要 PDF 圖，執行擷取")
else:
    print("[extract] 無 figures.json，執行擷取")
```

`need_extract = True` 時執行下列指令（**注意：會整份覆寫 figures.json 與 coverage.json**——HTML 版 manifest 會被 PDF 版取代；`figNN.png` 圖檔本身仍留在 img/ 不受影響，study/review 之後重跑會自行重建各自需要的 manifest）：

```
python "<SKILLS_ROOT>\paper-to-review\extract_figures.py" "<pdf_path>" "<pdf.parent>\Claude"
```

> **逐 Fig 覆蓋率確認（必做）**：讀（重用或新產的）`Claude/img/coverage.json` 的 `per_fig`，對每個 Fig 編號確認已對應到影像：`rendered_page` 直接通過；`embedded_candidate` 須由 Claude 在該頁 `fig_NN.png` 視覺找到對應圖，找不到則對其 `page` 補算繪（`extract_figures.py ... page <頁碼>`）。（走到這裡只會遇到這兩種值——`covered_by:"html"` 只存在於 HTML 版 manifest，而那種情況已在上方判準被導去重抽。）每個 Fig 都對應到影像後才生成投影片。
>
> 使用者明確要求「重新擷取」或懷疑圖檔損毀時，無視重用判準、強制重跑擷取。

產出（或重用）`Claude/img/fig_NN.png` 與 `Claude/img/figures.json`（只用 `status: ok` 的圖）。接著由 Claude **讀取各 `fig_NN.png` 視覺辨識**，比對 1a 的圖編號/圖說，把對應檔路徑填入 `fig_map[fig_id]['path']` 並設 `['exists']=True`。量測類向量圖若 `status≠ok`，改用 Phase 1c 的原頁算繪。完成後：

```python
missing = [k for k,v in fig_map.items() if not v['exists']]
print(f"Missing after PDF extraction: {missing}")
```

### 1b. 分配圖至章節（section_figs）

按 DOM 順序追蹤 `<h2>`/`<h3>` 標籤，每張圖歸屬到最近的前置 section header。

```python
from collections import OrderedDict

section_figs = OrderedDict()  # section_title -> [fig_num, ...]
current_sec  = "__intro__"
section_figs[current_sec] = []

SKIP = {'Abstract', 'References', 'Acknowledgment', 'Acknowledgements'}

for elem in soup.find_all(['h2','h3','div']):
    if elem.name in ('h2','h3'):
        text = elem.get_text(strip=True)
        if text and not any(s in text for s in SKIP):
            current_sec = text
            if current_sec not in section_figs:
                section_figs[current_sec] = []
    elif elem.name == 'div' and 'figure' in elem.get('class', []):
        fid = elem.get('id','')
        if fid in fig_map:
            section_figs[current_sec].append(fig_map[fid]['num'])

# Remove empty sections
section_figs = {k: v for k, v in section_figs.items() if v}
for sec, nums in section_figs.items():
    print(f"  [{sec}] → Figs {nums}")
```

### 1c. 缺圖補救（向量圖抽不到時）

某 Fig 在 `figures.json` 為 `status≠ok`（多為量測類向量圖）時，對含該圖的頁面用 `extract_figures.py` 的 page 模式算繪：

```
python "<SKILLS_ROOT>\paper-to-review\extract_figures.py" "<pdf_path>" "<pdf.parent>\Claude" page <頁碼>
```

產出 `Claude/img/page_N.png`；更新 fig_map 對應 entry 的 `path` 與 `exists=True`。**所有圖片皆來自根層 PDF，不使用 HTML 的 `_files/`。**

---

## Phase 2：自動生成投影片計畫

**所有判斷由 Claude 自動完成。** 流程：

```
讀 PDF text → 偵測圖對 → 生成 groupings → 識別 KEY_TERMS → 生成 desc_segments → 生成 CONCLUSION → 生成 OUTLINE
```

### 2a. 讀取 PDF 全文

```python
from pypdf import PdfReader

reader   = PdfReader(str(pdf))
pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
```

### 2b. 偵測 figure pairs

從 PDF 文字找出「被同一句話引用的圖對」——這些圖放在同一張 slide。

```python
import re

def find_paired_figs(pdf_text, total_figs):
    """Return set of (a, b) tuples where a < b and both figures cited together."""
    pairs = set()
    patterns = [
        r'[Ff]igs?\.\s*(\d+)\s+and\s+[Ff]ig\.\s*(\d+)',   # "Figs. 5 and Fig. 6"
        r'[Ff]igs?\.\s*(\d+)\s+and\s+(\d+)',                # "Figs. 5 and 6"
        r'[Ff]igs?\.\s*(\d+)[,\s]+(\d+)',                   # "Figs. 5, 6"
        r'[Ff]ig\.\s*(\d+)\s*[-–]\s*(\d+)',                 # "Fig. 5-6"
        r'\(Fig[s]?\.\s*(\d+)\s+and\s+(\d+)\)',             # "(Figs. 5 and 6)"
    ]
    for pat in patterns:
        for m in re.finditer(pat, pdf_text):
            a, b = int(m.group(1)), int(m.group(2))
            if (1 <= a <= total_figs and 1 <= b <= total_figs
                    and a != b and abs(a - b) <= 3):
                pairs.add((min(a, b), max(a, b)))
    return pairs

paired_figs = find_paired_figs(pdf_text, total_figs)
print(f"Detected pairs: {paired_figs}")
```

### 2c. 生成 groupings（section + mode + figs_tuple）

```python
def generate_groupings(section_figs, paired_figs):
    groups = []  # (section_title, mode, figs_tuple)
    for section, nums in section_figs.items():
        i = 0
        while i < len(nums):
            fn = nums[i]
            # Try to pair with next figure in same section
            if i + 1 < len(nums):
                fn2 = nums[i + 1]
                if (min(fn, fn2), max(fn, fn2)) in paired_figs:
                    groups.append((section, "two", (fn, fn2)))
                    i += 2
                    continue
            groups.append((section, "one", (fn,)))
            i += 1
    return groups

groupings = generate_groupings(section_figs, paired_figs)
for g in groupings:
    print(g)
```

### 2d. 識別 KEY_TERMS（Claude 判斷）

讀完 PDF 後，**由 Claude 從論文主旨識別**關鍵詞清單。這不是演算法，是語意理解：

**紅字標準（依重要性排序）：**
1. **設備/技術名稱**：論文提出的新裝置或電路名稱
2. **核心數據**：ESD 耐壓值、漏電數字、製程節點等直接支撐貢獻的數字
3. **新穎性聲明**：first、novel、proposed、state-of-the-art 等詞組
4. **關鍵性能指標**：達成什麼 class/level、compared to prior art 的改進量

```python
# Fill this list after reading the PDF — these exact strings (case-insensitive)
# will be marked red in desc_box AND conclusion_box
KEY_TERMS = [
    # Example from GaN ESD paper:
    # "first full-chip ESD",
    # "sub-driving gate ESD clamp",
    # "ultra-low leakage",
    # "< 50 nA",
    # "HBM Class 2",
    # "field-plate",
]
```

**規則：** 同一 slide 的 desc 文字中，`KEY_TERMS` 出現的片段標紅；其餘黑字。每張 slide 最多標 1-2 個紅色片段，避免過多紅字失去強調效果。

### 2e. 生成 desc_segments（全自動）

```python
def _first_sentence(text):
    i = text.find('.')
    return (text[:i+1]).strip() if i != -1 else text.strip()

def _pick_max_chars(text):
    """大寫密集（大寫佔英文字母 >30%，如 IGSS/IDSS、IG-VGS、TD1-TD10）→ 120；否則 130。
    落實 Pitfall #2 的兩檔上限——Arial Bold 大寫明顯較寬。"""
    letters = [c for c in text if c.isalpha()]
    uppers  = [c for c in letters if c.isupper()]
    return 120 if letters and len(uppers) / len(letters) > 0.30 else 130

def auto_trim_caption(caption, max_chars=130):
    """Fit within DESC_H (2 lines × 18pt).
    Use max_chars=130 for normal mixed-case text.
    Use max_chars=120 if text is uppercase-heavy (IGSS/IDSS, IG-VGS, TD1-TD10, etc.)
    — Arial Bold uppercase letters are significantly wider than lowercase.
    """
    if len(caption) <= max_chars:
        return caption
    fs = _first_sentence(caption)
    if len(fs) <= max_chars:
        return fs
    return caption[:max_chars - 3] + '...'

def colorize(text, key_terms, color="FF0000"):
    """Case-insensitive match; returns [(text, color_or_None)]."""
    segments = [(text, None)]
    for term in sorted(key_terms, key=len, reverse=True):  # longest first
        new_segs = []
        for seg, col in segments:
            if col is not None:          # already colored → skip
                new_segs.append((seg, col))
                continue
            lower_seg  = seg.lower()
            lower_term = term.lower()
            pos = 0
            while pos < len(seg):
                idx = lower_seg.find(lower_term, pos)
                if idx == -1:
                    new_segs.append((seg[pos:], None))
                    break
                if idx > pos:
                    new_segs.append((seg[pos:idx], None))
                new_segs.append((seg[idx:idx+len(term)], color))
                pos = idx + len(term)
        segments = new_segs
    return [(t, c) for t, c in segments if t]

def make_desc_segments(fig_nums, fig_map, key_terms):
    """Generate [(text, color_or_None)] for a one- or two-fig slide."""
    num_to_id = {v['num']: k for k, v in fig_map.items()}
    if len(fig_nums) == 1:
        cap = fig_map[num_to_id[fig_nums[0]]]['caption']
        text = auto_trim_caption(cap, _pick_max_chars(cap))
    else:
        cap_a = fig_map[num_to_id[fig_nums[0]]]['caption']
        cap_b = fig_map[num_to_id[fig_nums[1]]]['caption']
        combined = _first_sentence(cap_a) + " " + _first_sentence(cap_b)
        text = auto_trim_caption(combined, _pick_max_chars(combined))
    return colorize(text, key_terms)
```

### 2f. 生成 CONCLUSION（Claude 判斷 + colorize）

讀 PDF Conclusion 段落，**由 Claude 選出 3 個最重要的貢獻**，每點再用 `colorize()` 標紅。

**選 3 點的標準：**
1. 第一點：論文最核心的 claim（通常是"first"、"novel"開頭）
2. 第二點：直接量測數據支撐的性能貢獻
3. 第三點：應用場景或更廣的 implication

格式：每個 bullet 是 `[(text, color_or_None), ...]` list，用 `colorize()` 自動生成。

```python
# Example — generate from PDF Conclusion section via colorize():
def make_conclusion_point(full_text, key_terms):
    """full_text is one complete bullet sentence."""
    return colorize(full_text, key_terms)

# Build CONCLUSION after reading the paper:
CONCLUSION = [
    make_conclusion_point("First full-chip ESD for monolithic GaN gate driver ICs; ...", KEY_TERMS),
    make_conclusion_point("Proposed sub-driving gate ESD clamp achieves HBM Class 2 (2 kV) ...", KEY_TERMS),
    make_conclusion_point("Demonstrates ultra-low leakage < 50 nA @ 600 V in 200 mm GaN-on-Si process.", KEY_TERMS),
]
```

### 2g. 生成 OUTLINE（全自動）

Outline 頁除了章節清單，**必須在末尾附上本論文的完整 IEEE 格式引用**（不是「作者 et al., 年份」的簡寫）。

```python
def make_outline(section_figs, ieee_citation):
    """
    section_figs: OrderedDict with section titles as keys.
    ieee_citation: 完整 IEEE 格式引用字串（見下方「IEEE 引用格式」硬規則）。
    Returns lines for outline_box().
    """
    # Clean Roman numeral prefix from section titles
    clean_titles = []
    for title in section_figs.keys():
        cleaned = re.sub(r'^[IVX]+\.\s*', '', title).strip()
        clean_titles.append(cleaned)

    lines = [f"{i+1}.  {t}" for i, t in enumerate(clean_titles)]
    lines.append("")
    lines.append("Ref:")   # 不加前導空白：要與下方引用文字左緣對齊
    lines.append(ieee_citation)
    return lines

# 範例參數，填當前論文實際值，勿照抄
OUTLINE = make_outline(section_figs,
    'F. A. Altolaguirre and M.-D. Ker, “Power-rail ESD clamp circuit with diode-string ESD '
    'detection to overcome the gate leakage current in a 40-nm CMOS process,” <i>IEEE Trans. '
    'Electron Devices</i>, vol. 60, no. 10, pp. 3500–3507, Oct. 2013, doi: 10.1109/TED.2013.2274701.')
```

> 引用字串較長，`outline_box()` 中把 `Ref:` 之後的行字級降到 16pt（其餘 22pt），避免溢出。
> **斜體一定要標**：引用字串裡用 `<i>…</i>` 包住期刊名／會議名，`outline_box()` 會把它轉成斜體 run（2026-10-15 漏標被使用者抓到）。引號用彎引號 `“…”`、頁碼範圍用 en dash `–`（指南範例皆如此）。

#### IEEE 引用格式（硬規則，不得自行簡化）

正本依據：`<VAULT_ROOT>\論文\Group Meeting\IEEE Reference Style Guide for Authors.pdf`（IEEE Publication Operations, V 3.28.2025）。**格式有疑義一律以該 PDF 為準，不要憑印象寫。**

**期刊論文 Basic Format（該指南 p.15「M. Periodicals」）**：

```
J. K. Author, "Name of paper," Abbrev. Title of Periodical, vol. x, no. x, pp. xxx-xxx, Abbrev. Month, year, doi: xxx.
```

**會議論文 Basic Format（p.8）** ——注意只有會議論文才有 `in`：

```
J. K. Author, "Title of paper," in Abbreviated Name of Conf., (location optional), (Month and day(s) if provided) year, pp. xxx-xxx.
J. K. Author, "Title of paper," in Abbreviated Name of Conf., (location optional), year, pp. xxx–xxx, doi: xxx.   ← 有 DOI（p.8）
```

會議名縮寫照指南 p.7 表（Proceedings→Proc.、International→Int.、Symposium→Symp.、Conference→Conf.）＋ p.26 縮寫表（Reliability→Rel.、Physics→Phys.），會議名**斜體**（只斜體會議名，`in` 不斜體）。**地點與月日省略**（指南 p.8 帶 DOI 格式中地點標 optional；實驗室學長柯杰辰的 IEDM 引用即 `in IEDM Tech. Dig., 2025, pp. 1-4, doi: …`，2026-10-15 使用者指定以他為範本）。頁碼用 Xplore／Crossref 登記的頁碼（`api.crossref.org/works/<doi>` 的 `page`，例 `1–7`），不用論文頁尾的 `8C.3-1` 式編號。頁碼範圍用 en dash（指南範例）。作者名逐一對論文首頁（連字號名 `Jean-Jacques`→`J.-J.`；括號暱稱如 `(Paul)` 不列）；≤6 位全列，>6 位才用第一作者＋`et al.`。例：`S. Huang, S. Parthasarathy, Y. Zhou, J.-J. Hajjar, and E. Rosenbaum, “…,” in <i>Proc. IEEE Int. Rel. Phys. Symp. (IRPS)</i>, 2024, pp. 1–7, doi: 10.1109/IRPS48228.2024.10529384.`

**四個最常踩的坑**（2026-08-18 實際校對 IEEE Xplore 匯出字串時發現）：

| 坑 | 錯 | 對 |
|---|---|---|
| 期刊論文誤加 `in` | `in IEEE Transactions on Electron Devices` | `IEEE Trans. Electron Devices` |
| 期刊名沒縮寫 | `IEEE Transactions on Electron Devices` | `IEEE Trans. Electron Devices` |
| 縮寫後多留 `on` | `IEEE Trans. on Electron Devices` | `IEEE Trans. Electron Devices`（指南全文 `Trans. on` 出現 **0** 次） |
| 姓名縮寫多空格 | `M. -D. Ker` | `M.-D. Ker` |

其他要點：
- 作者一律「名字縮寫在前、姓在後」；≤6 位全列，>6 位用第一作者 + `et al.`（指南 p.4）。
- 論文標題用**句首大寫**（指南期刊範例皆如此），期刊名**斜體**。
- 收進正式期別的文章用**期別日期**（如 vol. 60 no. 10 → `Oct. 2013`），不是 early access 的 Date of Publication；early access 才用後者（指南 p.4）。
- `Electron Devices` 的 Electron **不加句點**（那是名詞「電子」，不是 Electronic 的縮寫；縮寫表中 `Electronic → Electron.` 才有句點）。
- 全部引用以句點結尾（含帶 DOI 者）。
- **⚠️ 不要直接貼 IEEE Xplore「Cite This」按鈕的字串**——它與官方 Reference Style 不一致（期刊論文也加 `in`、不縮寫期刊名、姓名縮寫間多空格），貼完必須手動修正上表四項。（會議論文本來就要 `in`，別誤刪。）

**實驗室範本（柯杰辰學長歷次報告，2026-10-15 使用者指定「他一定是對的」）**——格式拿不準時先對這兩條：
- 期刊：`Y. Ma et al., “Monolithically integrated bidirectional gate ESD protection scheme of p-GaN power HEMT by dual-gate device technology,” <i>IEEE Trans. Power Electronics</i>, vol. 40, no. 2, pp. 2721-2725, Feb. 2025.`（`Group Meeting\20251223\`）
- 會議：`S.-H. Hung et al., “Full-chip ESD for the monolithic GaN-based gate driver with ultra-low leakage current,” in <i>IEDM Tech. Dig.</i>, 2025, pp. 1-4, doi: 10.1109/IEDM50572.2025.11353697.`（`Group Meeting\20260428\`）
- 範本與指南不同的三處，**以指南為準**（使用者已知情）：①他把 `in` 也斜體 → 我們只斜體刊名／會議名 ②他頁碼用 `-` → 我們用 en dash `–` ③範本用 `et al.` 是因為作者 >6 位，≤6 位一律全列。

**資料來源（不准憑印象）**：作者全名看論文首頁；頁碼、出版年、刊名卷期看 Crossref `https://api.crossref.org/works/<doi>`（`page`、`published`、`volume`、`issue`、`container-title`）；DOI 無 HTML 時從 PDF 首頁側邊或頁尾抓。

**引用自查清單（產完 PPT 後逐條勾，任一條不過就修完重產）**：
1. 作者：名縮寫在前、連字號名 `J.-J.`、≤6 位全列並在最後一位前加 `, and`
2. 標題：句首大寫（專有名詞／縮寫保留大寫），彎引號，逗號在右引號內 `,”`
3. 期刊無 `in`；會議有 `in`（`in` 本身不斜體）
4. 刊名／會議名已縮寫（指南 p.7 會議表＋p.23 起縮寫表）且**在 PPT 裡實際是斜體**——用 python-pptx 讀 slide 2 印出 `font.italic=True` 的 run，必須恰好是刊名／會議名
5. 會議論文不放地點與月日；期刊放 `vol., no., pp., 月. 年`
6. 頁碼＝Crossref `page`、範圍用 en dash；有 DOI 就放 `doi: …`；全句以句點結尾
7. `Ref:` 與引用文字左緣對齊（匯出 slide 2 的 JPEG 目視）

> 慣例：**大綱第一項固定是 Introduction**（IEEE 論文第 I 節；模板 slide 2 的「I. Introduction」字樣即此提醒）。注意 `section_figs` 只含**有圖**章節（1b 會過濾空節）——若 Introduction 無圖而沒出現在 make_outline 結果裡，**手動把 `1.  Introduction` 補到 lines 開頭並重編號**（大綱要呈現論文全部章節、與論文同序）；補完首項仍不對才回頭檢查 1b 的章節解析。

### 2g-2. 生成 TITLE_INFO（第 1 頁 Title，全自動）

2026-10-20 使用者裁示：第 1 頁**全部自動填**，不再留給他手填。格式以實驗室學長柯杰辰 2026/9/1 VLSI 報告的 Title 頁為範本：

```
<論文完整題目>
Author: Tao-Yi Hung, Li-Wei Chu, Wun-Jie Lin, Jam-Wem Lee, and Kuo-Ji Chen
Published in: IEEE Symposium on VLSI Technology and Circuits        ← 會議／期刊名斜體
Date of Conference: 14 ~ 18, June, 2026
Reporter: Yu-You Luo / Advisor: Chun-Yu Lin / Date: 2026/9/1
```

```python
# 範例參數，填當前論文實際值，勿照抄
TITLE_INFO = {
    "title": "Reduced RC Time Constant High Voltage Tolerant Supply Clamp for ESD Protection in 16nm FinFET Technology",
    "authors": ["Shudong Huang", "Srivatsan Parthasarathy", "Yuanzhong Zhou", "Jean-Jacques Hajjar", "Elyse Rosenbaum"],
    "venue": "IEEE International Reliability Physics Symposium (IRPS)",
    "date_label": "Date of Conference",      # 期刊論文改 "Date of Publication"
    "date": "14 ~ 18, April, 2024",          # 期刊論文：期別日期 "October 2013"
    "report_date": "2026/10/20",             # 報告日 YYYY/M/D（月日不補 0）
}
```

**資料來源（不准憑印象）**：
- `title`：論文完整題目，照論文首頁大小寫（不是 IEEE 引用的句首大寫）。
- `authors`：**全名**，照論文首頁順序；與 Crossref `author`（`given`＋`family`）交叉核對。括號暱稱不列。
- `venue`：Crossref `container-title` 的正式全名，**去掉開頭年份**（`2024 IEEE International Reliability Physics Symposium (IRPS)` → `IEEE International Reliability Physics Symposium (IRPS)`）；不縮寫。
- `date`：會議論文取 Crossref `event.start`／`event.end` 的 `date-parts`，寫成 `D1 ~ D2, Month, YYYY`（月份英文全名；單日會議寫 `D, Month, YYYY`；跨月寫 `30, March ~ 2, April, 2026`）。Crossref 沒有 `event` → 查 Xplore 論文頁的「Date of Conference」，再查不到就問使用者。期刊論文：`date_label="Date of Publication"`，`date` 用期別月份年份（`October 2013`；early access 才用 Xplore 的 Date of Publication）。
- `report_date`：**報告日**＝記憶 group-meeting 報 paper 班表中「今天以後最近的一次」（含今天）；班表沒有或都已過 → 問使用者一次。
- `Reporter: Yu-You Luo`、`Advisor: Chun-Yu Lin` 固定，寫在 3a 的 `fill_title_slide()` 裡，不放進 TITLE_INFO。

### 2h. 組裝最終 plan

```python
num_to_id = {v['num']: k for k, v in fig_map.items()}

plan = []
for section, mode, figs in groupings:
    desc_segs = make_desc_segments(figs, fig_map, KEY_TERMS)
    plan.append((section, mode, figs, desc_segs))

# Add Conclusion as last content slide
plan.append(("V. Conclusion", "conclusion", (), CONCLUSION))
```

**Phase 2 自查點**：輸入＝pdf_text、section_figs、fig_map。輸出＝paired_figs、groupings、KEY_TERMS、desc_segments、CONCLUSION、OUTLINE、TITLE_INFO、plan。檢查＝TITLE_INFO 六欄皆非空、作者數與論文首頁一致、`venue` 開頭無年份；plan 涵蓋 section_figs 每張圖恰一次；CONCLUSION 恰 3 點；OUTLINE 第一項為 Introduction；每張 slide 的 desc ≤130（大寫密集 ≤120）字元；OUTLINE 的引用字串過 2g「引用自查清單」第 1–6 條（刊名／會議名已用 `<i>…</i>` 包住）。

---

## Phase 3：生成 PPTX

### 3a. 完整生成腳本（先讀組裝說明）

**gen_ppt.py 必須是一支自含腳本**：把 Phase 1（解析 HTML → fig_map/section_figs）與 Phase 2（plan/OUTLINE/CONCLUSION/KEY_TERMS/TITLE_INFO）的程式碼、或它們算出的結果（以字面量寫死），與下方 Phase 3a 主體**組進同一支檔案**——下方腳本單獨執行會因 `fig_map`/`plan`/`OUTLINE` 未定義而 NameError。**存放位置：`<paperfolder>\Claude\gen_ppt.py`**（用 Write 工具建立）。

`desc_box` 接受 `[(text, color_or_None)]` segments（與 conclusion 格式相同）。

```python
"""
Paper-to-PPT generator.
Run via PowerShell (not bash) for Chinese path compatibility.
Close PowerPoint before running to avoid PermissionError.
"""
import os, re, copy
from collections import OrderedDict
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu, Pt
from lxml import etree
from pptx.oxml.ns import qn

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: PIL not available — images use bounding-box sizing")

# ── User settings ─────────────────────────────────────────────────────────────
PAPER_DIR = r"<論文資料夾根層完整路徑>"          # 與 Claude/ 同層、含論文 PDF
BASE      = os.path.join(PAPER_DIR, "Claude")     # 副產物目錄
IMG_DIR   = os.path.join(BASE, "img")             # PDF 擷取圖（fig_NN.png / page_N.png）
OUT       = os.path.join(PAPER_DIR, "PPT.pptx")   # 成品輸出至根層

# Template: paper-root copy, then Claude/ copy, then canonical fallback (never ask)
CANONICAL_TPL = r"<SKILLS_ROOT>\paper-to-ppt\slides.pptx"
_root_tpl     = os.path.join(PAPER_DIR, "slides.pptx")
_claude_tpl   = os.path.join(BASE, "slides.pptx")
TPL           = _root_tpl if os.path.exists(_root_tpl) else (_claude_tpl if os.path.exists(_claude_tpl) else CANONICAL_TPL)

# ── Template geometry (memorized) ─────────────────────────────────────────────
prs = Presentation(TPL)
HDR_X, HDR_Y  = 611560, 548680
HDR_W, HDR_H  = 7848872, 719137
CT_LEFT        = 500000
CT_TOP         = HDR_Y + HDR_H + 90000      # 1357817
CT_RMAR        = 400000
CT_W           = int(prs.slide_width) - CT_LEFT - CT_RMAR   # 8244000
FOOTER_TOP     = 6408738
CLEARANCE      = 20000
# 圖下方不放「Fig. N」標示（2026-10-15 使用者裁示拿掉）→ 圖片高度直接延伸到 footer 上方
DESC_H         = 500000      # 2-line capacity: spcBef(12700)+2×18pt(457200)+buffer; DO NOT reduce below 500000（前提：desc_box 的 tIns/bIns=0）
DESC_GAP       = 20000
IMG_TOP        = CT_TOP + DESC_H + DESC_GAP                  # 1877817
IMG_H          = FOOTER_TOP - CLEARANCE - IMG_TOP            # 4510921
CT_H           = FOOTER_TOP - CLEARANCE - CT_TOP             # 5030921
custom_layout  = prs.slide_layouts[1]

BULLET_CHAR = "\uF06C"  # Wingdings large ● — NEVER paste literal char (editors silently drop it)
BULLET_SZ   = "1800"

# ── XML helpers ───────────────────────────────────────────────────────────────
def _set_para_hanging_indent(p, spc_before_pts=1):
    pPr = p._p.get_or_add_pPr()
    pPr.set('algn', 'just')
    pPr.set('marL', '381000')
    pPr.set('marR', '43180')
    pPr.set('indent', '-342900')
    if pPr.find(qn('a:lnSpc')) is None:
        lnSpc = etree.SubElement(pPr, qn('a:lnSpc'))
        etree.SubElement(lnSpc, qn('a:spcPct')).set('val', '100000')
    if pPr.find(qn('a:spcBef')) is None:
        spcBef = etree.SubElement(pPr, qn('a:spcBef'))
        etree.SubElement(spcBef, qn('a:spcPts')).set('val', str(spc_before_pts * 100))

def _append_wingdings_bullet(p_elem):
    r1 = etree.SubElement(p_elem, qn('a:r'))
    rPr1 = etree.SubElement(r1, qn('a:rPr'))
    rPr1.set('dirty','0'); rPr1.set('b','0'); rPr1.set('sz', BULLET_SZ)
    etree.SubElement(rPr1, qn('a:latin')).set('typeface', 'Wingdings')
    etree.SubElement(rPr1, qn('a:cs')).set('typeface', 'Wingdings')
    etree.SubElement(r1, qn('a:t')).text = BULLET_CHAR
    r2 = etree.SubElement(p_elem, qn('a:r'))
    rPr2 = etree.SubElement(r2, qn('a:rPr'))
    rPr2.set('dirty','0'); rPr2.set('b','0'); rPr2.set('spc','430'); rPr2.set('sz', BULLET_SZ)
    etree.SubElement(rPr2, qn('a:latin')).set('typeface', 'Times New Roman')
    etree.SubElement(rPr2, qn('a:cs')).set('typeface', 'Times New Roman')
    etree.SubElement(r2, qn('a:t')).text = " "

def _append_text_run(p_elem, text, bold=True, size_pt=18, color=None):
    # CRITICAL: solidFill MUST come BEFORE a:latin (OOXML schema order)
    r = etree.SubElement(p_elem, qn('a:r'))
    rPr = etree.SubElement(r, qn('a:rPr'))
    rPr.set('dirty','0'); rPr.set('sz', str(int(size_pt * 100))); rPr.set('b', '1' if bold else '0')
    if color:
        fill = etree.SubElement(rPr, qn('a:solidFill'))
        etree.SubElement(fill, qn('a:srgbClr')).set('val', color)
    etree.SubElement(rPr, qn('a:latin')).set('typeface', 'Arial')
    etree.SubElement(r, qn('a:t')).text = text

# ── Slide builders ────────────────────────────────────────────────────────────
def header_font_size(text):
    words = text.strip().split()
    if len(words) == 1: return 36
    return 30 if len(text) * 0.215 > 7.5 else 32

def add_header_bar(slide, text):
    txBox = slide.shapes.add_textbox(Emu(HDR_X), Emu(HDR_Y), Emu(HDR_W), Emu(HDR_H))
    tf = txBox.text_frame; tf.word_wrap = True
    tf._txBody.bodyPr.set('anchor', 'ctr')
    p = tf.paragraphs[0]
    pPr = p._p.get_or_add_pPr()
    pPr.set('algn','ctr'); pPr.set('eaLnBrk','1'); pPr.set('hangingPunct','1')
    run = p.add_run()
    run.text = text; run.font.size = Pt(header_font_size(text))
    run.font.bold = True; run.font.name = "Arial"
    rPr = run._r.get_or_add_rPr()
    rPr.set('lang','en-US'); rPr.set('altLang','zh-TW'); rPr.set('dirty','0')
    bodyPr = tf._txBody.bodyPr
    for child in list(bodyPr):
        if child.tag in (qn('a:noAutofit'), qn('a:normAutofit'), qn('a:spAutoFit')):
            bodyPr.remove(child)
    etree.SubElement(bodyPr, qn('a:normAutofit'))

def _get_img_path(fig_num, fig_map):
    """Resolve image path from fig_map; fall back to extracted fig."""
    num_to_id = {v['num']: k for k, v in fig_map.items()}
    fid = num_to_id.get(fig_num)
    if fid and fig_map[fid]['exists']:
        return str(fig_map[fid]['path'])
    # Fallback: PDF-extracted image in Claude/img/
    for name in (f"fig_{fig_num:02d}.png", f"page_{fig_num}.png"):  # 刻意不含 figNN.png：HTML 圖不用於投影片（解析度政策）
        alt = os.path.join(IMG_DIR, name)
        if os.path.exists(alt):
            return alt
    raise FileNotFoundError(f"Fig. {fig_num} not found in {IMG_DIR} — 重跑 Phase 1a-2 從 PDF 擷取")

def _place_image(slide, img_path, x, y, w, h):
    if HAS_PIL:
        with Image.open(img_path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        dw = int(iw * scale); dh = int(ih * scale)
        dx = x + (w - dw) // 2; dy = y + (h - dh) // 2
        slide.shapes.add_picture(img_path, Emu(dx), Emu(dy), Emu(dw), Emu(dh))
    else:
        slide.shapes.add_picture(img_path, Emu(x), Emu(y), Emu(w), Emu(h))

def desc_box(slide, segments):
    """
    segments: list of (text, color_or_None) tuples.
    Wingdings ● bullet is prepended automatically.
    Key points: pass color="FF0000" for red text.
    """
    if isinstance(segments, str):           # backward-compat: plain string
        segments = [(segments, None)]
    txBox = slide.shapes.add_textbox(Emu(CT_LEFT), Emu(CT_TOP), Emu(CT_W), Emu(DESC_H))
    tf = txBox.text_frame; tf.word_wrap = True
    tf._txBody.bodyPr.set('anchor', 't')
    # 預設上緣內距 45720 EMU 不在 DESC_H 預算內 → 單張高圖時第二行會被圖片白邊蓋住（2026-10-15 實測）
    tf._txBody.bodyPr.set('tIns', '0'); tf._txBody.bodyPr.set('bIns', '0')
    p = tf.paragraphs[0]
    _set_para_hanging_indent(p, spc_before_pts=1)
    _append_wingdings_bullet(p._p)
    for text, color in segments:
        _append_text_run(p._p, text, bold=True, size_pt=18, color=color)

# 圖下方不加「Fig. N」標示文字框（2026-10-15 使用者裁示）
def one_fig(slide, fig_num, desc_segments):
    img_path = _get_img_path(fig_num, fig_map)
    desc_box(slide, desc_segments)
    _place_image(slide, img_path, CT_LEFT, IMG_TOP, CT_W, IMG_H)

def two_figs(slide, fig_a, fig_b, desc_segments):
    gap    = 80000
    half_w = (CT_W - gap) // 2
    desc_box(slide, desc_segments)
    _place_image(slide, _get_img_path(fig_a, fig_map), CT_LEFT,           IMG_TOP, half_w, IMG_H)
    _place_image(slide, _get_img_path(fig_b, fig_map), CT_LEFT+half_w+gap, IMG_TOP, half_w, IMG_H)

def outline_box(slide, lines):
    txBox = slide.shapes.add_textbox(Emu(CT_LEFT), Emu(CT_TOP), Emu(CT_W), Emu(CT_H))
    tf = txBox.text_frame; tf.word_wrap = True
    ref_seen = False
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if i > 0:
            p.space_before = Pt(11)   # 0.5 × 22pt
        if line.strip().startswith("Ref:"):
            ref_seen = True
        # <i>...</i> 標出要斜體的段落（期刊名／會議名，見 2g「IEEE 引用格式」）
        for k, piece in enumerate(re.split(r"</?i>", line)):
            if not piece:
                continue
            run = p.add_run()
            run.text = piece
            # 章節列 22pt；"Ref:" 起的完整 IEEE 引用較長，降為 16pt 以免溢出版面
            run.font.size = Pt(16) if ref_seen else Pt(22)
            run.font.bold = True; run.font.name = "Arial"
            run.font.italic = (k % 2 == 1)

def conclusion_box(slide, points):
    txBox = slide.shapes.add_textbox(Emu(CT_LEFT), Emu(CT_TOP), Emu(CT_W), Emu(CT_H))
    tf = txBox.text_frame; tf.word_wrap = True
    tf._txBody.bodyPr.set('anchor', 'ctr')   # vertical center
    for i, segments in enumerate(points[:3]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _set_para_hanging_indent(p, spc_before_pts=12 if i > 0 else 1)
        _append_wingdings_bullet(p._p)
        for text, color in segments:
            _append_text_run(p._p, text, bold=True, size_pt=18, color=color)

# ── Title slide（2g-2 TITLE_INFO；2026-10-20 使用者裁示全部自動填）─────────────
TITLE_AREA_TOP, TITLE_AREA_BOT = 742578, 2780928   # 模板 AutoShape 4（題目底框）上下緣
TITLE_MAX_H_PT = 160                                # 題目可用高度（pt），超過就縮字

def _join_authors(names):
    if len(names) == 1: return names[0]
    if len(names) == 2: return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]

INFO_BOT       = 4869160 - 60000                    # 文字框 1 下緣上限＝模板分隔線（Line 3）上方
INFO_MAX_H_PT  = (INFO_BOT - 2924943) / 12700       # 文字框 1（top 2924943）可用高度

def _wrap_lines(text, width_emu, size):
    """估計行數：Arial 粗體平均字寬約 0.55 em（2026-10-20 實測約 0.52）。只是初估，渲染 QA 才算數。"""
    cap, lines, cur = int(width_emu / 12700 / (0.55 * size)), 1, 0
    for w in text.split():
        add = len(w) if cur == 0 else len(w) + 1
        if cur + add > cap and cur > 0:
            lines += 1; cur = len(w)
        else:
            cur += add
    return lines

def _title_font_pt(text, box_w):
    """放得進題目框的最大字級（行高 1.2）。"""
    for size in (48, 44, 40, 36, 32, 28, 24):
        lines = _wrap_lines(text, box_w, size)
        if lines * size * 1.2 <= TITLE_MAX_H_PT:
            return size, lines
    return 24, lines

def _info_font_pt(texts, box_w):
    """文字框 1 三行（作者多、會議名長時會折行）放得進分隔線上方的最大字級；行高 1.25、段距 0.2 em。"""
    for size in (24, 22, 20, 18, 16):
        n = sum(_wrap_lines(t, box_w, size) for t in texts)
        if n * size * 1.25 + len(texts) * size * 0.2 <= INFO_MAX_H_PT:
            return size
    return 16

def _set_label_line(p, label, value, italic=False):
    """模板段落＝[標籤 run, 冒號 run, (值 run)]；沿用標籤 run 的格式，冒號統一半形。"""
    runs = p.runs
    runs[0].text = label
    runs[1].text = ": "
    for r in runs[2:]:
        p._p.remove(r._r)
    new_r = copy.deepcopy(runs[0]._r)
    new_r.find(qn('a:t')).text = value
    new_r.find(qn('a:rPr')).set('i', '1' if italic else '0')
    runs[1]._r.addnext(new_r)        # 放在冒號後、a:endParaRPr 前（OOXML 順序）

def fill_title_slide(slide, info):
    shapes = {sh.text_frame.text.strip().split("\n")[0][:6]: sh for sh in slide.shapes if sh.has_text_frame}
    title_sh, box1, box2 = shapes["Title"], shapes["Author"], shapes["Report"]
    # 題目：改既有 run 的字，保留模板格式；字長就縮字，並在底框內垂直置中
    size, lines = _title_font_pt(info["title"], title_sh.width)
    run = title_sh.text_frame.paragraphs[0].runs[0]
    run.text = info["title"]; run.font.size = Pt(size)
    title_sh.text_frame.word_wrap = True
    h = int(lines * size * 1.2 * 12700)
    title_sh.top = max(TITLE_AREA_TOP, (TITLE_AREA_TOP + TITLE_AREA_BOT) // 2 - h // 2)
    # 文字框 1：Author／Published in／Date of ...，刪掉模板的空行
    # 模板框只有 6.6 吋寬，五位作者＋會議全名在 24pt 會溢出壓到 Reporter（2026-10-20 實測）
    # → 加寬到與題目框同寬，再依內容縮字
    lines = [f"Author: {_join_authors(info['authors'])}",
             f"Published in: {info['venue']}",
             f"{info['date_label']}: {info['date']}"]
    box1.left, box1.width = title_sh.left, title_sh.width
    size = _info_font_pt(lines, box1.width)
    ps = box1.text_frame.paragraphs
    _set_label_line(ps[0], "Author", _join_authors(info["authors"]))
    _set_label_line(ps[1], "Published in", info["venue"], italic=True)
    _set_label_line(ps[3], info["date_label"], info["date"])
    box1.text_frame._txBody.remove(ps[2]._p)
    for p in box1.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(size)
    # 文字框 2：Reporter／Advisor 固定，Date＝報告日
    ps = box2.text_frame.paragraphs
    _set_label_line(ps[0], "Reporter", "Yu-You Luo")
    _set_label_line(ps[1], "Advisor", "Chun-Yu Lin")
    _set_label_line(ps[2], "Date", info["report_date"])

# ── Main ──────────────────────────────────────────────────────────────────────
# 模板固定 6 張：0=Title（本腳本依 TITLE_INFO 填入，見 2g-2）
#   1=Outline（本腳本填入）
#   2=「I. Introduction」、3/4=空白 —— 模板內建「版面示意頁」：
#     2 提醒大綱第一項固定是 Introduction；3/4 示範「標題＋底線＋內容」版面。
#     只供人打開模板參考用，成品不需要 → 生成時必須刪除，否則會夾在成品中間
#   5=Thanks（最後搬到結尾）
# Slide 0 (Title): auto-filled from Phase 2g-2
fill_title_slide(prs.slides[0], TITLE_INFO)
# Slide 1 (Outline): auto-generated OUTLINE from Phase 2g
outline_box(prs.slides[1], OUTLINE)

# 刪除模板示意頁 index 2-4（由高到低刪，索引才不會位移）
# ⚠️ 只 remove sldId 不夠：頁面 part 仍留在檔案裡，之後 add_slide 會產生同名 slideN.xml
#    → 存出的 zip 有重複檔名（UserWarning: Duplicate name），PowerPoint 打不開（2026-10-15 實測）。
#    必須 drop_rel 移除 part，再把留下的 Title/Outline/Thanks 重新編號（Thanks 原本是 slide6.xml，不改會再撞一次）。
from pptx.opc.packuri import PackURI
sldIdLst = prs.slides._sldIdLst
for _i in (4, 3, 2):
    _sid = sldIdLst[_i]
    prs.part.drop_rel(_sid.rId)
    sldIdLst.remove(_sid)
for _k, _s in enumerate(prs.slides):
    _s.part.partname = PackURI(f"/ppt/slides/slide{_k + 1}.xml")
thanks_elem = sldIdLst[-1]          # 刪完示意頁後，最後一張就是 Thanks

# Content + Conclusion slides: auto-generated plan from Phase 2h
for header, mode, figs, data in plan:
    sl = prs.slides.add_slide(custom_layout)
    add_header_bar(sl, header)
    if mode == "one":
        one_fig(sl, figs[0], data)
    elif mode == "two":
        two_figs(sl, figs[0], figs[1], data)
    elif mode == "conclusion":
        conclusion_box(sl, data)

# Move Thanks slide to end
sldIdLst.remove(thanks_elem)
sldIdLst.append(thanks_elem)

prs.save(OUT)
print(f"Saved: {OUT}")
```

### 3b. 執行

```powershell
# 必須用 PowerShell（中文路徑）
python "<paperfolder>\Claude\gen_ppt.py"

# 若 PermissionError（PowerPoint 開著）:
# 不要強制結束 PowerPoint（會殺掉所有視窗、未存檔的簡報直接遺失）。
# 請使用者先存檔並關閉 PowerPoint，他確認後再重跑：
python "<paperfolder>\Claude\gen_ppt.py"
```

**Phase 3 自查點**：輸入＝plan／OUTLINE／CONCLUSION／TITLE_INFO＋模板檔。slide 1 的題目、`Author:`、`Published in:`（值 run 斜體）、`Date of …:`、`Date:` 皆已填值、無全形冒號（python-pptx 讀出確認）。輸出＝`<paperfolder>\PPT.pptx`。檢查＝byte-check BULLET_CHAR 通過（見 Phase 4 前置）；腳本印出 `Saved:` 路徑；成品張數＝2（Title＋Outline）＋內容張數＋1（Thanks），示意頁 0 張；執行輸出**不得出現 `Duplicate name`**（出現＝檔案已損毀，PowerPoint 會打不開，QA 匯出會報 COM 例外）；圖片下方無「Fig. N」標示；slide 2 的斜體 run 恰為刊名／會議名、`Ref:` 與引用左緣對齊（2g 引用自查清單第 4、7 條）。

---

## Phase 4：QA — 匯出每張投影片 JPEG

> 本 Phase 輸入＝PPT.pptx；輸出＝`qa_slides\slide-NN.jpg`（1280×960）；自查＝下方逐張確認清單。

**Windows**——用 skill 附的 Python 腳本（late binding，不靠 Office type library；實測下方 PowerShell 寫法報 `TYPE_E_CANTLOADLIBRARY`、這支正常）。只會關掉它自己開的 PowerPoint；PowerPoint 原本就開著時只關它開的這份簡報：

```powershell
python "<SKILLS_ROOT>\paper-to-ppt\qa_export_win.py" "<paperfolder>\PPT.pptx" "<paperfolder>\qa_slides"
```

**Mac**——Mac PowerPoint 匯出 PDF → `pdftoppm` 切成 1280×960 JPEG。檔案先複製進 PowerPoint 的沙盒夾（免授權視窗）；只關這份簡報、不結束 PowerPoint。

> **前置條件：PowerPoint 要已經開著至少一個視窗（任何簡報都行）。** 剛啟動、停在起始畫面（範本挑選）沒有視窗時，AppleScript 開檔會回 `-9074`，換 `open alias`／`open -a` 也一樣。遇到 -9074 → 請使用者在 PowerPoint 開一份空白簡報，**下面區塊原文不改**重跑即可；或 Claude 自己先跑 `osascript -e 'tell application "Microsoft PowerPoint" to make new presentation'`，**等約 4 秒**（`count of windows` 變成 1 才算好，立刻查還是 0），再跑下面區塊（PowerPoint 冷啟動停在起始畫面那種情形未另測）。



```bash
SB=~/Library/Containers/com.microsoft.Powerpoint/Data/Documents/ppt_qa
P="<paperfolder>"
rm -rf "$SB" && mkdir -p "$SB" && cp "$P/PPT.pptx" "$SB/qa.pptx"
osascript -e 'on run argv
  set src to item 1 of argv
  set dst to (POSIX file (item 2 of argv)) as text
  tell application "Microsoft PowerPoint"
    set n0 to count of presentations
    open (POSIX file src)
    set t to 0
    repeat while (count of presentations) = n0
      delay 1
      set t to t + 1
      if t > 120 then error "PowerPoint 120 秒內沒有開好檔案"
    end repeat
    save active presentation in dst as save as PDF
    close active presentation saving no
  end tell
end run' "$SB/qa.pptx" "$SB/qa.pdf"
rm -rf "$P/qa_slides" && mkdir -p "$P/qa_slides" && pdftoppm -jpeg -scale-to-x 1280 -scale-to-y 960 "$SB/qa.pdf" "$P/qa_slides/slide"
ls "$P/qa_slides" | wc -l   # 應＝投影片張數
```

**舊 PowerShell 寫法**（Windows 備援；部分環境會報 type library 錯，留著給 Office 修復後用）：

```powershell
$pptxPath = "完整路徑\PPT.pptx"
$outDir   = "完整路徑\qa_slides"
New-Item -ItemType Directory -Force $outDir | Out-Null

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = [Microsoft.Office.Core.MsoTriState]::msoTrue
$prs = $ppt.Presentations.Open($pptxPath)
for ($i = 1; $i -le $prs.Slides.Count; $i++) {
    $prs.Slides.Item($i).Export("$outDir\slide-$('{0:D2}' -f $i).jpg", "JPG", 1280, 960)
}
$prs.Close(); $ppt.Quit()
```

**執行前：先 byte-check BULLET_CHAR**（寫成 `Claude\check_bullet.py` 再執行，勿用 `python -c` 單行式）

```python
content = open(r"<paperfolder>\Claude\gen_ppt.py", encoding="utf-8").read()
idx = content.find('BULLET_CHAR')
print([hex(ord(c)) for c in content[idx:idx+25]])
# 正確（擇一）：'0x5c','0x75','0x46','0x30','0x36','0x43'（escape 寫法 \uF06C，建議）或 '0xf06c'（原義字元）
```

若引號間空無一物（`...'0x22','0x22'...`）＝子彈已遺失，把該行改回 `BULLET_CHAR = "\uF06C"` 再執行腳本。

COM 匯出失敗（無 Office／COM 報錯）→ 不阻斷交付：回報使用者改手動開啟 PPT.pptx 逐張確認（對照下方清單）。

使用者逐張確認：
- Header bar 字號合適（1 word=36pt, 多字=32/30pt）
- Wingdings ● 出現在 desc box 和 Conclusion（無 ● = BULLET_CHAR 遺失）
- 紅字正確顯示（desc 和 conclusion）
- 圖片正確置中不變形
- desc 文字確認為 2 行，未溢出進圖片區
- Title slide 已填好（題目未溢出底框、Author／Published in／Date of … 三行、會議／期刊名斜體、冒號半形、Reporter／Advisor／Date＝報告日）；Thanks 在最後
- **Outline 之後直接是第一張內容頁**——無殘留的「I. Introduction」示意頁或空白頁（有＝腳本漏了刪 index 2-4）
- **Outline 頁末尾有完整的 IEEE 格式引用**，且逐項對過 Phase 2g「四個最常踩的坑」：期刊論文無 `in`、期刊名已縮寫、縮寫後沒有多餘的 `on`、姓名縮寫無多餘空格

---

## 字型規則速查

| 元素 | 字型 | 大小 | 粗體 |
|------|------|------|------|
| Header（1 word） | Arial | 36pt | 是 |
| Header（多字，短） | Arial | 32pt | 是 |
| Header（多字，長） | Arial | 30pt | 是 |
| desc（● 後正文） | Arial | 18pt | 是 |
| Outline 列表 | Arial | 22pt | 是 |
| Conclusion bullet | Arial | 18pt | 是 |

**最小 header 字號永遠是 30pt。**

---

## 紅字使用原則

| 位置 | 標紅標準 |
|------|---------|
| `desc_box` 所有 slide | KEY_TERMS 自動 colorize；同一句最多 1-2 個紅色片段 |
| `conclusion_box` | KEY_TERMS + 核心數據；每 bullet 至少 1 個紅色片段 |
| Outline | 不標紅 |
| Header bar | 不標紅 |

**紅字太多 = 沒有強調。** 若 colorize 後整句超過 30% 都是紅字，收窄 KEY_TERMS。

---

## 常見問題

| 問題 | 解法 |
|------|------|
| 圖片抽不到 | 確認根層 PDF 存在並重跑 Phase 1a-2；向量量測圖改用 `extract_figures.py` page 模式算繪（Phase 1c）|
| `PermissionError` 存檔失敗 | PowerPoint 開著。請使用者先存檔並關閉 PowerPoint，確認後再重跑；**不要 `Stop-Process` 強制結束**（未存檔的簡報會遺失） |
| 紅字未顯示 | `solidFill` 必須在 `a:latin` 之前（OOXML 順序，`_append_text_run` 已處理）|
| 圖片變形 | 安裝 PIL（`pip install Pillow`）；HAS_PIL = True 時自動等比例縮放 |
| 中文路徑 UnicodeError | 必須用 PowerShell 執行，不能用 bash |
| Wingdings ● 消失（無子彈） | `BULLET_CHAR` 中 U+F06C 被編輯器靜默丟棄；執行前用 byte-check 驗證；修復：用 Edit 工具把該行改回 escape 寫法 `BULLET_CHAR = "\uF06C"`（不要用 PowerShell Replace 或 heredoc，傳參層會再丟一次該字元） |
| Wingdings ● 顯示為方框 | PowerPoint 字型快取；重開 PPT 通常可解 |
| 偵測到的 pairs 不對 | 手動調整 `paired_figs` 再執行 generate_groupings |
| Conclusion 點選錯 | 讀 PDF Conclusion 段落重新選 3 點，重跑 Phase 2f |
