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

## 安裝

```
/plugin marketplace add <你的GitHub帳號>/claude-study-skills
/plugin install study-skills@claude-study-skills
```

裝完在新視窗打 `/skills` 應該看得到五個。

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

## 維護：同步本機版本（給作者）

本機開發版與這個公開版是兩份分開的副本。改完本機版後：

```
python tools/sync.py       # 從本機 .my-skills 同步 + 去個人化 + 檢查
git add -A && git commit -m "..." && git push
```

`tools/sync.py` 會做四件事：

1. 把個人路徑換成佔位符
2. 排除不公開的檔案（`slides.pptx`）
3. 重新套上「公開版專屬修改」（`PUBLIC_PATCHES`）——同步是覆蓋式的，這些差異每次都要重貼
4. 掃描殘留個資，**有殘留就 exit 1**（別在紅燈時 push）

只想檢查不寫檔：`python tools/sync.py --check`。

若印出 `[PATCH-MISS]`，代表源版改寫過被 patch 的那一段 → 回去更新 `PUBLIC_PATCHES` 再跑。

## 授權

MIT，見 `LICENSE`。
