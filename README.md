# Study Skills for Claude Code

五個把 **PDF 讀成中文結構化筆記** 的 Claude Code skills。輸出全部是 Markdown，主要針對 [Obsidian](https://obsidian.md) 調校（VS Code 也能讀，只是摺疊區塊會退化成一般引用）。

| Skill | 輸入 | 輸出 |
|---|---|---|
| **paper-to-study** | 期刊／會議論文 PDF | 理解型筆記（多層心智圖、High→Low 層次、貢獻列表、Reference 分析）＋ 完整中文翻譯 |
| **paper-to-review** | 同上 | 批判評讀筆記：主張 vs 證據、來源溯源、結果 7 問、誠實局限、研討會討論題 |
| **paper-to-ppt** | 論文 HTML ＋ PDF | 學術風格 PPTX（需自備模板，見下方限制） |
| **book-to-study** | 教科書單一章節 PDF ＋ 整本書 PDF | 精讀筆記 ＋ 逐句中文翻譯 ＋ L0→L3 分層理解複習 |
| **handout-to-study** | 上課投影片講義 PDF | 逐頁講解（投影片兩頁並排）＋ 重點複習（分層＋公式速查＋摺疊自測題） |

每個 skill 都寫成「**執行者只讀得到這一份檔案**」的規格：逐 Phase 的機械判準、腳本合約（CLI 簽名／輸出檔名／哨兵字串／exit code／覆寫行為）、失敗路徑、最終驗收清單。

## 安裝或更新

**最快的方式**：把這個 repo 的連結貼給 Claude Code，說「照 README 幫我安裝或更新」。

Claude Code 請先判斷是哪一種安裝：

### A. 環境包版（`~/.claude/kit-venv` 存在）

這是針對 macOS 改過的版本，**不要跑下方 B 的 plugin 指令，也不要移除 `~/.claude/skills/` 裡的任何資料夾**。只補上翻譯檔嵌圖，在終端機執行：

```
curl -fsSL https://raw.githubusercontent.com/royal0421/claude-study-skills/main/tools/update_env_kit.py -o /tmp/update_env_kit.py
~/.claude/kit-venv/bin/python /tmp/update_env_kit.py
```

印出 `[DONE]` 或 `[OK]` 就完成，重開視窗，路徑不用重換。印出 `[ABORT]` 代表沒有改動，把訊息回報給使用者。

### B. 一般安裝（其他情況）

1. 檢查 `~/.claude/skills/` 底下有沒有手動複製的同名資料夾（`paper-to-study`、`paper-to-review`、`paper-to-ppt`、`book-to-study`、`handout-to-study`）。有的話，手動版會和 plugin 版重複，先問使用者要不要移除，不要自己刪。
2. 在終端機依序執行：

```
claude plugin marketplace add royal0421/claude-study-skills
claude plugin marketplace update claude-study-skills
claude plugin install study-skills@claude-study-skills
claude plugin update study-skills@claude-study-skills
```

已經裝過時，第一行或第三行可能回報已存在，繼續跑下一行即可。

3. 請使用者重開視窗，打 `/skills` 應該看得到五個。
4. 更新會蓋掉已安裝的檔案，下一節的路徑佔位符要重換一次。

## 使用前必改：路徑佔位符

這些 skill 原本寫給一套固定的資料夾結構，公開版把個人路徑換成了佔位符。**跑之前先全域搜尋以下字串，換成你自己的路徑**：

| 佔位符 | 意思 | 例 |
|---|---|---|
| `<VAULT_ROOT>` | 你的 Obsidian vault 根目錄 | `C:\Users\me\Documents\vault` |
| `<SKILLS_ROOT>` | 這個 repo 的 `skills\` 資料夾（腳本都在裡面） | `C:\Users\me\.claude\...\skills` |
| `<REPO_ROOT>` | 這個 repo 的根目錄 | |
| `<CLAUDE_HOME>` | `~\.claude` | |
| `<HOME>` | 使用者家目錄 | |
| `<課程資料夾>` / `<講義資料夾>` / `<課程MOC>` | handout-to-study 用來掛課程筆記的位置 | |

## 環境需求

- **Claude Code**（skills 機制）
- **Python 3**，各 skill 用到的套件寫在各自 SKILL.md 的「套件需求」節：
  - `pymupdf`（PDF 頁數／文字層／render，全部 skill 都要）
  - `pillow`（裁圖）
  - `python-pptx`（paper-to-ppt）
  - `matplotlib`（book-to-study 的自繪圖）
- 指令範例是 **Windows / PowerShell 5.1** 寫法（沒有 `&&`，路徑用反斜線）。macOS／Linux 要自行改寫路徑分隔符。

### handout-to-study 的版面 CSS

`skills/handout-to-study/buck-slides.css` 要複製到 `<VAULT_ROOT>/.obsidian/snippets/`，再到「設定 → 外觀 → CSS 程式片段」開啟 `buck-slides`。**沒開的話投影片會變成上下排列、心智圖會超出畫面。**

### 在 macOS 上用一般安裝

- SKILL.md 的 `python` 換成 `python3`，`Test-Path <路徑>` 換成 `[ -e "<路徑>" ] && echo yes`，反斜線路徑換成斜線。
- 缺套件用 `python3 -m pip install --user --break-system-packages <套件>`。
- paper-to-study 的 IEEE 網頁存檔要用 Chrome 或 Brave 按 `⌘S`，格式選「網頁，完整」；Safari 存不出 `_files` 資料夾。

## 已知限制

- **paper-to-ppt 沒有附模板**：原本的 `slides.pptx` 是他人製作的實驗室模板，不隨這個 repo 散布。要用的話自備一份 16:9 模板，命名 `slides.pptx` 放進 `skills/paper-to-ppt/`，並依 SKILL.md「模板幾何常數」節校正版面數值。
- **paper-to-study 的 IEEE 全文下載需要校園 VPN**，且只在 IEEE Xplore 可存取的網路環境有效。
- 產出語言是**繁體中文**。要別的語言得改 SKILL.md 裡的體例規定。
- 這些 skill 假設你用 Obsidian 的 callout（`> [!question]-`）與 mermaid；換閱讀器會有部分語法退化。

## 為什麼規則寫得這麼細

每一條硬規則背後都是一次踩過的坑，例如：

- mermaid 節點裡放兩組 `$$...$$` → 整張圖變 `Error parsing Mermaid diagram!`
- `<summary>` 是 HTML block，裡面的 `$公式$` 不會被 KaTeX 解析 → 摺疊自測題一律改用 Obsidian callout
- 心智圖「一個畫面看完」的關鍵是**改變佈局方向**（鏈狀用 `graph LR`），不是縮小字級
- 圖片剪裁的哨兵計數只證明「有產出」，不證明「配對正確」→ 一律目視抽查

所以 SKILL.md 都很長。那是刻意的：規則寫得夠死，弱模型才不會自由發揮。

## 授權

MIT，見 `LICENSE`。
