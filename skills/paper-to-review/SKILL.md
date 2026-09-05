---
name: paper-to-review
description: 將學術 PDF 論文轉換為一份「批判評讀型」結構化 Markdown 筆記（Obsidian 相容）。聚焦於：主張 vs. 證據、來源溯源、結果 7 問判讀、圖表判讀、誠實局限、研討會討論題、教學式重排。與 paper-to-study 互補（後者做理解+翻譯，本 skill 做批判與教學評讀）。圖片來源優先序：HTML 存檔圖片資料夾（*_files/）→ PyMuPDF 從 PDF 抽原圖 → matplotlib 自繪 / Mermaid。觸發時機：用戶提供 PDF 並要求「評讀/批判分析/做成可講給別人聽的精讀」；說 /paper-to-review；想對單篇論文做研討會級別的深度評讀。
---

# Paper to Review Skill（批判評讀型 Markdown）

把單篇學術 PDF 轉成一份 **Obsidian 相容** 的批判評讀筆記。本 skill 的價值在「閱讀紀律」，不在輸出格式；**不產生 LaTeX/PPT**。

## 呼叫方式

```
/paper-to-review <pdf_path>
```

- 評讀 md（檔名為 `論文簡稱.md`，**僅論文簡稱、不加任何 `評讀_` 前綴或 `_評讀` 後綴**）產出到 **pdf 所在資料夾（pdf.parent）根層**。檔內 H1 維持中文敘述標題、frontmatter `title` 為論文真實標題。
- 抽圖 / matplotlib / page-render / figures.json / _extracted.txt / CSS 等副產品進 **`pdf.parent/Claude/`**（圖片在 `Claude/img/`）。

若未提供路徑，詢問：「請提供 PDF 路徑（可直接拖曳至終端機）：」

**論文簡稱推導（與 paper-to-study 同一規則，保證 `[[論文簡稱_理解]]` 等連結不斷）**：同層已存在 `*_理解.md`／`*_翻譯.md` 或既有評讀 md → 沿用其簡稱；否則取標題 2–4 個英文關鍵詞、`-`/`_` 相接、≤40 字元。決定後印出，全程用同一字串。

**套件需求**：pdfplumber 或 PyMuPDF（fitz，抽文字擇一）、PyMuPDF（extract_figures.py 必需）、Pillow（import_html_figures.py 軟依賴：缺了印 `NO_HTML_FALLBACK_PDF  (Pillow 未安裝)` 並 exit 2，走 PDF 退路）、beautifulsoup4（讀 HTML metadata 時）。缺 → `pip install` 重試一次 → 仍缺回報使用者。

## 與 paper-to-study 的分工

| | paper-to-study | paper-to-review（本 skill） |
|---|---|---|
| 目的 | 讀懂 + 翻譯 | 批判評讀 + 教學重組 |
| 產出 | 理解筆記 + 中文翻譯 | 一份批判評讀筆記 |
| 偏向 | 吸收理解 | 評斷可信度、邊界、可講述性 |

---

## ⚠️ 相容性規則（產出檔必守）

| 規則 | 說明 |
|------|------|
| ✅ YAML frontmatter | 檔案頂部必須有 `---` frontmatter |
| ✅ `<sub>` 下標 | `V_t1`/`Vt1` → `V<sub>t1</sub>` |
| ✅ Obsidian callout | 重點/精隨/局限/討論用 `> [!abstract]` `> [!note]` `> [!warning]` `> [!question]` |
| ✅ Mermaid（水平不溢出） | 流程圖用 **`flowchart LR`（水平）**，但**必須壓到不需左右拉**：(1) 控制「階數（橫向深度）」≤4–5，必要時**合併節點**（如把多個觸發/步驟併成一格）；(2) 節點文字短、用 `<br/>` 斷行；(3) 開頭加 `%%{init: {'flowchart': {'nodeSpacing': 18, 'rankSpacing': 28}, 'themeVariables': {'fontSize': '11px'}}}%%` 縮小字體與間距；(4) 下標用 unicode（M₂₁、L₁）非 `<sub>`（mermaid 內不渲染 HTML）。縮排 2 空格、非 tab。若仍過寬，再縮短標籤或拆成兩張小圖 |
| ✅ 相對路徑圖片 | 所有圖片用相對路徑，圖存於 `./Claude/img/` |
| ✅ 圖片排版 + 並排 | 所有嵌入圖一律用 `<img src width>`，**固定 `width="48%"`**。兩張並排＝同一段落（中間無空行）放兩個 `<img>`、各 48%；單張＝一個 `<img width="48%">`，**與並排時等大** |
| ❌ 禁用 `<style>` | 不可內嵌 style 標籤 |
| ❌ 禁用 HTML table | 文字表一律用 GFM；HTML 僅限圖片排版 |

## 下標轉換對照表（生成文字時套用，code block 內不轉）

| 原始 | 轉換後 | 原始 | 轉換後 |
|------|--------|------|--------|
| `V_DD` / `VDD` | `V<sub>DD</sub>` | `V_SS` / `VSS` | `V<sub>SS</sub>` |
| `V_t1` / `Vt1` | `V<sub>t1</sub>` | `V_h` / `Vh` | `V<sub>h</sub>` |
| `V_BD` / `VBD` | `V<sub>BD</sub>` | `V_clamp` / `Vclamp` | `V<sub>clamp</sub>` |
| `I_t2` / `It2` | `I<sub>t2</sub>` | `I_ESD` / `IESD` | `I<sub>ESD</sub>` |
| `R_on` / `Ron` | `R<sub>on</sub>` | `C_ESD` | `C<sub>ESD</sub>` |

---

## Phase 1：論文擷取與批判閱讀

### 1a. 擷取 PDF 文字（寫成 `_extract_text.py` 後執行，勿用 stdin 管線）

**重用判準**：`Claude\_extracted.txt` 已存在（通常是先跑過 /paper-to-study）→ 直接重用、跳過本步。不存在才建立 `_extract_text.py`（放 `<pdf.parent>\Claude\`；`Claude\` 不存在先建立），用 pdfplumber 或 PyMuPDF 逐頁抽文字寫入 `Claude\_extracted.txt`，再讀回分析。IEEE 雙欄論文一律左右欄分開抽再拼（同 paper-to-study Phase 1a 的 crop 法），避免欄位交錯。若 pdfplumber 未裝可改用 PyMuPDF（fitz）。

### 1b. 批判閱讀紀律（核心，不可省）

- **區分主張與證據**：論文「宣稱」的 vs 它「實際證明」的。
- **來源溯源**：每條重要主張/數據標來源（§節 / Fig / Table / 頁）。
- **標記不確定**：無證據者標「待證」，不可代為腦補。
- **不杜撰**：看不懂或抽不到的內容明講，不假裝理解、不發明細節。
- 全文術語一致。

### 1c. 論文 metadata 擷取（供 frontmatter 填寫）

**優先順序**（先查 `pdf.parent/Claude/` 下是否有 `*.html`）：
- **有 HTML（IEEE Xplore 存檔）**：metadata 內嵌在 JS 物件 `xplGlobal.document.metadata`（**不是** `<meta citation_*>` 標籤）。寫成 .py 執行：
  ```python
  import re, json
  txt = open(html_path, encoding="utf-8", errors="replace").read()
  m = re.search(r'xplGlobal\.document\.metadata\s*=\s*(\{.*?\});', txt, re.DOTALL)
  d = json.loads(m.group(1))
  # title=d["title"]; authors=[a["name"] for a in d["authors"]];
  # journal=d["publicationTitle"]; year=d["publicationYear"]; doi=d["doi"];
  # institution=d["authors"][0]["affiliation"]
  ```
  找不到該物件時退路：讀 `<meta property="og:title">` 取標題、regex `"doi"\s*:\s*"([^"]+)"` 取 DOI。
- **無 HTML**：從 PDF 第 1 頁文字推斷標題、作者，regex 抓 DOI（`Digital Object Identifier` 或 `10\.\d{4,}/\S+`）；抓不到的欄位標「待補」。

**Phase 1 自查點**：輸入＝PDF（＋選用 Claude/ 內 HTML）。輸出＝`Claude\_extracted.txt`、metadata。檢查＝_extracted.txt 非空；title/doi 至少一項非「待補」。

---

## Phase 2：生成批判評讀筆記

**輸出位置**：`[short_title].md`（**檔名僅論文簡稱、不加前綴或後綴**）放在 **PDF 所在資料夾（pdf.parent）根層**；抽圖、matplotlib 輸出、page render、figures.json、_extracted.txt、CSS 等副產品統一放 **`pdf.parent/Claude/`**（圖片放 `Claude/img/`）。

依下列結構生成（採「教學邏輯」順序，非論文章節順序）：

````
---
title: "[FULL PAPER TITLE]"
authors: ["[AUTHOR 1]", "[AUTHOR 2]"]
journal: "[JOURNAL]"
year: [YEAR]
doi: "[DOI]"
tags: [paper-review, <領域關鍵字，如 T-coil/CDM/GaN/wireline/HS-IF/VF-TLP，供知識樹自動分類>]
created: [YYYY-MM-DD]
type: paper-critical-appraisal
---

> tags 內務必含可分類的 ESD 領域關鍵字（Phase 5 知識樹分類依據）。

# [PAPER TITLE SHORT] — 批判評讀

> [!abstract] TL;DR
> **問題**：[一句話]
> **方法**：[一句話]
> **洞見**：[一句話]

## 一、主張 vs. 證據

| 論文宣稱 | 實際證明了什麼 | 證據來源 | 評讀 |
|---------|--------------|---------|------|
| [宣稱] | [實證] | [§/Fig/Table] | ✅充分 / ⚠️部分 / ❗待證 |

## 二、動機與問題定位

[為何此問題重要、前人不足在哪]

## 三、關鍵洞見

[最核心、非顯而易見的一點]

## 四、方法與實作

[技術細節；流程用 Mermaid，參數比較用 GFM 表]

## 五、論文原圖判讀

[每張圖：為何放、各元件意義、怎麼讀、是否支持結論、caveat；圖標「From the paper」]

## 六、結果判讀（7 問框架）

> [!question] 對 [Fig./Table X] 的判讀
> 1. 答什麼問題：
> 2. 比什麼：
> 3. 軸/欄意義：
> 4. 趨勢/異常：
> 5. 作者結論：
> 6. 結論成立嗎：
> 7. 缺什麼 baseline/workload：

## 七、優點與局限

> [!note] 優點
> [這篇做得好的地方]

> [!warning] 局限（公平、不輕蔑）
> [強假設 / 資料少 / 缺 baseline / 可行性 / 擴展性]

## 八、研討會討論問題與解答

[3–6 題，每題後附「博士級解答」。解答水準＝一個已徹底讀懂本文、準備充分上研討會、熟悉此領域的研究生/博士生會給的回答：具體、有根據、能區分「代理證明了什麼 vs 機制宣稱什麼」、能談最差情況與轉移性。格式如下，每題一個小標題＋一個 note callout 解答]

### Q1. [考驗貢獻邊界的問題]

> [!note] 解答
> [博士級、具體、有來源依據的回答，必要時引用 §/Fig/Table]

[Q2…Qn 同上格式]

### Q[n]. 看完這篇論文，你學到了什麼？

> [!note] 解答（轉移性洞見）
> [博士級反思：不只複述，要萃取可遷移到其他題目的洞見——例如關鍵思路、跨領域移植、貢獻定位、驗證與失效模式的對應、方法論。條列 4–6 點]

## 九、總結與延伸

- [Takeaway 1–5]
- **只記一件事**：[一句]
- **後續方向**：[具體可評估的方向]
````

**Phase 2 自查點**：輸出＝`<pdf.parent>\論文簡稱.md`。檢查＝九大區塊齊全且非佔位；「主張 vs. 證據」表 ≥3 列；七問逐問有內容；討論題 3–6 題、每題有解答 callout；全文搜尋 `待補`／`TODO` 為 0 筆。

---

## 圖片五來源（依優先順序，不可跳層捏造）

1. **HTML 圖片資料夾（最優先）**：若 `Claude/` 下有 IEEE Xplore 存檔 `*.html` 及其同名 `*_files/` 資產夾，圖片一律先從這裡匯入（論文原始向量渲染圖，乾淨且含 (a)(b)(c) 子圖）。**優先重用既有匯入，否則才匯入**：
   - **`Claude/img/figures.json` 已存在且每筆 `status:"html"`（或 coverage.json 頂層 `source:"html"`）**（典型流程「先 study 再 review」）→ 直接重用 `figNN.png`／`tableN.png`，不要重匯。注意：figures.json 每筆的 `source` 欄是原始檔名（如 keel5.gif），**判斷來源請看 `status` 欄**。
   - **figures.json 存在但為 PDF 版（每筆 `status:"ok"`，通常是 ppt 之後跑過、把 manifest 覆寫成 PDF 版）而 `img/` 內仍有 `figNN.png`** → HTML 圖檔還在：重跑 `import_html_figures.py` 重建 HTML 版 manifest 後照本來源走（覆寫回 HTML 版無害，ppt 之後重跑會自行再抽它要的 PDF 版）。
   - **不存在**（單獨直接跑 review）→ 執行 `python "<SKILLS_ROOT>\paper-to-review\import_html_figures.py" "<paperfolder>\Claude"`。印 `HTML_FIGURES_OK <n>`（exit 0）代表成功，全篇圖以 `coverage.json.figs_detected` 為準、檔名 `img/figNN.png`、`per_fig.covered_by:"html"`（確定涵蓋）；印 `NO_HTML_FALLBACK_PDF`（exit 2）代表無 HTML 資產夾 → 改走來源 2。
   - 內嵌路徑 `./Claude/img/figNN.png`，標「From the paper」。嵌入前由 Claude **讀 `img\figNN.png` 視覺確認**對應正確 Fig 編號。
2. **PDF 原圖（無 HTML 資產夾時的退路；優先重用既有擷取，否則才抽）**：`extract_figures.py` 在 study 與 review 資料夾**各有一份、內容 byte-identical**（2026-07-06 SHA256 實測相同；**改任一份必同步另一份**），ppt 則跨資料夾呼叫 review 這份。輸出 `Claude/img/fig_NN.png` + `figures.json` + `coverage.json`。判斷依據＝該檔是否存在：
   - **存在** → load `figures.json`（沿用 `status: ok` 內嵌圖 + `rendered_page` 向量圖後備）與 `coverage.json`（逐 Fig 覆蓋表）。
   - **不存在** → 才執行 `python "<SKILLS_ROOT>\paper-to-review\extract_figures.py" "<pdf>" "<paperfolder>\Claude"`。

   圖落在 `Claude/img/`，內嵌路徑用 `./Claude/img/<filename>`，標「From the paper」。唯有懷疑圖檔損毀或要求重新擷取時才強制重跑覆蓋。
   - **逐 Fig 覆蓋率確認（必做）**：讀 `coverage.json` 的 `per_fig`，對每個 Fig 編號確認已對應到影像；`embedded_candidate` 須由 Claude 視覺找到對應圖，找不到則對其 `page` 補算繪（見下方來源 4）。每個 Fig 都對應到影像後才繼續。
3. **matplotlib 自繪 / Mermaid**：當論文缺合適圖、或概念需簡化教學時：
   - matplotlib：寫 `_make_figs.py`（標籤用英文/符號避免 CJK 缺字），圖存 `Claude/img/*.png`，標「自繪/示意」。
   - Mermaid：流程/結構關係用 mermaid 原生語法，標「自繪/示意」。
4. **頁面算繪（render_page）**：採 PDF 退路、且量測向量圖 extract 失敗（status≠ok）時，對含該圖的頁面執行：
   ```
   python "<SKILLS_ROOT>\paper-to-review\extract_figures.py" "<pdf>" "<paperfolder>\Claude" page <頁碼>
   ```
   產出 `Claude/img/page_N.png`，內嵌路徑 `./Claude/img/page_N.png`，標「原頁算繪」。
5. **文字提及**：以上都不可行時，改用文字描述圖的內容；**絕不捏造論文未提供的數據。**

### 並排與否（自動判斷，不問使用者）

對「決定要嵌入的圖」逐一檢查——當**相鄰的兩張圖性質相配**就並排（同段落兩個 `<img width="48%">`、中間無空行），否則單張（一個 `<img width="48%">`）。配對條件（滿足任一）：
- 同類型：兩張都是電路/架構圖，或都是量測/模擬結果圖；
- 對照關係：概念圖 ↔ 其細化/實作圖（如簡化電路 ↔ 模擬等效電路）、單一條件 ↔ 其參數掃描、before ↔ after、(a) ↔ (b) 子圖。

並排時於圖說標「（左）」「（右）」並加一句左右對照的解說。**不相鄰、主題不同、或為獨立概念示意圖 → 維持單張。**「五、論文原圖判讀」段落依此規則自動決定排版。

---

## Phase 3：後處理

執行（postprocess.py 與本 SKILL.md 同目錄；呼叫前確保 `<pdf.parent>\Claude` 已存在——Phase 1 擷取步驟會建立，本腳本自己**不會**建資料夾）：

```
python "<SKILLS_ROOT>\paper-to-review\postprocess.py" "<pdf.parent>\Claude" "<pdf.parent>\<論文簡稱>.md"
```

此腳本：下標轉換（跳過 code block）、移除誤加的 `<style>`、保留 `<img>` 圖片排版、生成選用 CSS（CSS 存入 `Claude/`）。

**Phase 3 自查點**：輸入＝評讀 md＋`Claude\`。輸出＝轉換後的 md、`Claude\` 內 CSS。檢查＝腳本輸出無 error；抽 1 處確認 V_DD/VDD 已轉 `<sub>`；md 內無 `<style>` 標籤。

---

## Phase 4：最終清單

- [ ] frontmatter 存在、無 `<style>`
- [ ] 討論題 3–6 題且每題附解答 callout；七問逐問非空；無佔位文字（`待補`／`TODO`）殘留
- [ ] callout（abstract/note/warning/question）皆使用
- [ ] 九大區塊齊全且有實質內容（非佔位）
- [ ] 主張 vs 證據表、結果 7 問、圖表判讀、討論題確實填實
- [ ] 圖片來源優先序正確：有 HTML `*_files\` 時由 import_html_figures.py 匯入（figNN.png）優先，否則才走 PDF 原圖/render_page；自繪/Mermaid/文字為後續層級。路徑用 `./Claude/img/`，可解析
- [ ] 下標使用 `<sub>`

---

## Phase 5：加入論文總覽（自動執行）

> 產出評讀 md 後自動執行。**索引主體是評讀 md**；理解/翻譯 md 不單獨列入論文索引，但會由評讀檔 footer（5b-2）連出，一起顯示在 Graph。
> 論文總覽（論文 paper 關係圖）：`<VAULT_ROOT>\論文\論文總覽.md`
> 該檔**不存在**（被移動/改名）時 → **中止 Phase 5**、回報使用者路徑失效；不要自行新建一份總覽。
> 前提：論文資料夾位於 `<VAULT_ROOT>\論文\` 之下（標準工作流）。論文不在 Vault 內（暫放他處測試等）→ **跳過 Phase 5** 並告知使用者原因，不要把 Vault 外的檔案掛進知識樹。
> 只編輯 md 內容，**不移動任何檔案**。
> **前置依賴**：Reference 連線（5e）以各論文「理解檔」的 `### 各 Reference 簡介` 表（paper-to-study 產出，標題乾淨）為主要依據——預期使用流程為**先跑 `/paper-to-study` 再跑 `/paper-to-review`**。理解檔不存在時退回解析 PDF References，準度較低。

### 5a. 自動推斷（不詢問使用者）
- 評讀 md 檔名（本次產出，type: paper-critical-appraisal）。
- **分類**：讀評讀 md 的 frontmatter `tags`，對照下表**由上而下**逐列檢查——tags 與該列觸發詞有任一交集（比對不分大小寫；連字號與空格視同，如 `T-coil`＝`t-coil`＝`T coil`；以**整個 tag 字串**相等為準、不做子字串比對——例：tag `CDM` 不命中觸發詞 `CDM-internal`）→ 定案為該列分類，**不再看後面的列**（先命中先贏。例：tags 同時含 GaN 與 T-coil → 序 1 先命中 → 歸「寬能隙（GaN/SiC）」）。全表掃完無命中（含 tags 只有 ESD／CDM／HBM／MM／paper-review 這類泛詞與等級規格詞——**刻意不設為觸發詞**，防測試格變垃圾桶）→ 歸「_未分類」。分類名必須與論文總覽的 `###` 標題**逐字一致**（含全形括號與底線）。

  | 序 | tags 含（任一） | → 分類（＝總覽 `###` 標題） |
  |---|---|---|
  | 1 | GaN, SiC, wide-bandgap, HEMT, 2DEG | 寬能隙（GaN/SiC） |
  | 2 | T-coil, HS-IF, high-speed, high-speed-IO, SerDes, wireline, wireline-receiver, PCIe, USB | 高速介面 |
  | 3 | RF, LNA, PA, mmWave, K-band, Ka-band, transceiver | RF 與毫米波 |
  | 4 | gate-driver, power-IC, DC-DC, LDO, automotive, LIN, CAN, high-voltage | 功率與高壓應用 |
  | 5 | FinFET, GAA, nanosheet, SOI, FD-SOI, advanced-node | 先進 CMOS 節點 |
  | 6 | BCD, SiGe, 3D-IC, chiplet, TSV, interposer | 特殊平台與整合 |
  | 7 | SEED, TVS, system-level, board-level | 系統級協同（SEED） |
  | 8 | cross-domain, cross-power-domain, internal-circuit, CDM-internal | 跨域與內部電路防護 |
  | 9 | full-chip, whole-chip, pad-ring, IO-ring, ESD-bus, power-rail, rail-based | 全晶片防護網路 |
  | 10 | trigger-circuit, false-trigger, mis-trigger, latch-on | 觸發與誤觸發免疫 |
  | 11 | power-clamp, RC-clamp, RC-triggered, transient-clamp, static-clamp, active-clamp, clamp | 電源軌 Clamp |
  | 12 | SCR, LVTSCR, DTSCR, MLSCR, thyristor, holding-voltage | SCR 家族 |
  | 13 | GGNMOS, GDPMOS, ggMOS, gcNMOS, gate-grounded, ballasting | MOS 防護元件 |
  | 14 | diode, STI-diode, gated-diode, poly-diode, diode-string, BJT | 二極體與 BJT |
  | 15 | snapback, ESD-mechanism, It2, second-breakdown, thermal-failure, device-physics | 元件物理與失效機制 |
  | 16 | TCAD, compact-model, SPICE-model, ESD-simulation, mixed-mode | TCAD 與緊湊模型 |
  | 17 | ERC, PERC, ESD-CAD, EDA, ESD-check, verification-flow | ESD 驗證 CAD |
  | 18 | IEC-61000, IEC, HMM, ESD-gun, gun-test, system-test | 系統級測試與標準 |
  | 19 | TLP, VF-TLP, correlation, test-method, waveform, characterization | 測試方法與關聯性 |
  | 20 | EMMI, OBIRCH, failure-analysis, latch-up, EOS, reliability | 失效分析與可靠度 |

  排序邏輯（維護本表時參考，執行時只照表跑）：平台／應用軸（序 1–6）最能代表論文賣點故最前；防護層級軸（序 7–15）由外（全晶片）往內（元件）排；方法學軸（序 16–20）殿後——測試詞幾乎每篇 ESD 論文都帶，設計軸全沒命中才判為方法學論文。論文總覽任一格 ≥6 篇會觸發總覽開頭註記的「分裂條款」——屆時同步改本表該列的寫入目標與 5d 排除清單。另：序 18 的 HMM＝human metal model（系統級放電測試標準），非 HBM 筆誤。
- **一句話說明**：從評讀 md 的 TL;DR 摘「方法/洞見」，格式 `作者, 期刊 年份，[核心貢獻]`。

### 5b. 論文索引加連結（新增、無翻譯子項、幂等）
在「論文索引」對應分類下加（評讀檔名＝論文簡稱，故連結即 `[[論文簡稱]]`）：
`- [[論文簡稱]] — 作者, 期刊年份，一句話說明`
**不處理既有理解條目**（使用者自行清理 legacy）。若同一 `[[論文簡稱]]` 已存在則更新該行、不重複新增。分類不存在則先建 `### 分類名` section。**索引列維持每篇一行、不加 `_理解`/`_翻譯` 子項**（理解/翻譯改由下步 5b-2 從評讀檔連出）。

### 5b-2. 評讀檔連向理解/翻譯（三檔成串、避免子檔孤立）
在**評讀 md（`論文簡稱.md`）末尾**加一行 footer（冪等，已存在同內容則略過）：
`<sub>理解/翻譯見 [[論文簡稱_理解]]、[[論文簡稱_翻譯]]。</sub>`
- 只連**實際存在**的同層檔（`論文簡稱_理解.md` / `論文簡稱_翻譯.md`，由 paper-to-study 產出）；缺哪個就不連哪個。
- 用意：論文索引只掛評讀檔一個節點，理解/翻譯靠此 footer 連到評讀檔 → Graph 上「評讀→理解、評讀→翻譯」三檔串成一串，**不會因 `showOrphans:false`（隱藏孤立點）而消失**。

### 5c. 跨論文比較表加一行
在「跨論文比較」表末尾加：
`| [[論文簡稱\|簡稱 年份]] | 保護架構 | 製程 | 目標介面 | 核心挑戰 |`
四欄從評讀 md 的方法/實作/局限等內容摘取。

### 5d. 建立 Vault 標題對照表
掃 `<VAULT_ROOT>\論文\` 下所有 md（論文筆記都在這；**刻意不掃整個<VAULT_ROOT>\**，避免掃進修課等無關檔案——2026-07-06 與使用者確認的範圍），篩選：frontmatter `type` 為 `paper-critical-appraisal` **或** `paper-comprehension`（後者供反向連結比對）；排除翻譯檔（`type: paper-translation`）與 MOC（如 `論文總覽.md`、`ESD book總覽.md`、`研究總覽.md`、`我的論文總覽.md`、`<VAULT_ROOT>總覽.md`）。讀各檔 frontmatter `title` → 建「完整標題 → md 檔名」對照。ESD book 文獻統一對應 `[[ESD book總覽]]`。

### 5e. Reference 雙向連結（必備，須產生 Graph View 箭頭）
**方向規則**：被引用者（先發表）→ 引用者（後發表）；實作上在「**被引用者的 md**」裡加「**引用者的 `[[連結]]`**」。
**取得某篇 References 的來源優先序**：(i) 該篇同 title 的理解檔之 `### 各 Reference 簡介` 表（標題乾淨）；(ii) 否則解析 PDF References 章節（`Claude/_extracted.txt` 末段，`[n] 作者, "標題," …`）。比對一律用**正規化模糊比對**對照 5d 的 Vault 標題表。機械判準：兩標題各自小寫化、去標點，取長度 ≥4 的英文詞集合，交集÷較短集合 ≥0.6 → 命中；介於 0.4–0.6 → 不自動連結，列入 5f「未比對到的引用」交人工確認。

新增評讀檔 X（論文 P_X）時，**兩種情形都要處理**：
- **情形 A：P_X 引用了知識樹裡的舊論文 P_Y**（讀 P_X 的 References，命中 Vault 中的 P_Y）→ 在 **P_Y 的 md** 末尾加 `後續 [[X 論文簡稱]] 引用並評讀了本論文。`（箭頭 P_Y → P_X；連結用 X 評讀檔名＝論文簡稱）。
- **情形 B：知識樹裡某舊論文 P_Z 引用了 P_X**（對樹中現有各論文 P_Z，**依同一來源優先序讀 P_Z 的 References**——優先 P_Z 理解檔的「各 Reference 簡介」表——看是否含 P_X 標題）→ 在 **新評讀檔 X 的 md**「與其他工作/定位」末尾加 `本論文為 [[P_Z]] 的參考文獻之一。`（箭頭 P_X → P_Z）。

連結加在對應 md 的「與其他工作/定位」段落末尾；已存在則略過；無命中略過並於 5f 列出「未比對到的引用」供人工檢查。

### 5f. 完成輸出
```
[OK] 論文總覽.md 已更新
     分類：[分類名]　新增：[[論文簡稱]]
     比較表：已加入一行
[OK] 理解/翻譯 已連結至評讀檔（footer，三檔成串）：[[論文簡稱_理解]]、[[論文簡稱_翻譯]]（缺者略過）
[OK] Reference 雙向連結：情形A（P_X→引用的舊論文）[摘要]；情形B（引用 P_X 的舊論文）[摘要]；未比對到的引用：[清單]
下一步：Obsidian Ctrl+G 開 Graph View 確認節點與箭頭方向。
```

**注意**：ESD Book 文獻不走此流程（連結加在 `ESD book總覽.md`）；理解/翻譯 md **不單獨列入論文索引**（改由評讀檔 footer 連出、三檔成串）；不移動任何檔案。

**Phase 5 自查點**：輸入＝評讀 md、`論文總覽.md`、（優先）理解檔的 Reference 表。輸出＝論文總覽.md 更新、評讀檔 footer、雙向 Reference 連結。檢查＝5f 輸出區塊逐項印出；新增的每個 `[[連結]]` 目標檔案實際存在；重跑不重複新增（冪等）；「未比對到的引用」清單已列出交人工。
