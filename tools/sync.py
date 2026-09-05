# -*- coding: utf-8 -*-
"""把本機 .my-skills 的 skill 同步成這個 repo 的公開副本（去個人化）。

用法（在 repo 根目錄）：
    python tools/sync.py            # 同步 + 檢查
    python tools/sync.py --check    # 只檢查有無殘留個資，不寫檔

流程：
  1. 從 SRC 複製 SKILLS 清單裡的 skill 到 <repo>/skills/
  2. 逐檔做路徑替換（個人路徑 → 佔位符）
  3. 排除私人檔案（EXCLUDE_FILES）
  4. 保留只存在於公開版的檔案（KEEP_PUBLIC_ONLY，例如附給別人用的 CSS）
  5. 全域掃描 BLACKLIST，有殘留就 exit 1（**不要在殘留未清乾淨時 push**）

exit code：0 = 乾淨；1 = 有殘留或來源不存在
"""
import argparse
import os
import re
import shutil
import sys

SRC = r'C:\Users\royal\.my-skills\skills'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(REPO, 'skills')

SKILLS = ['paper-to-study', 'paper-to-review', 'paper-to-ppt',
          'book-to-study', 'handout-to-study']

# 不公開：他人製作的資產（檔案屬性含他人姓名）
EXCLUDE_FILES = {'slides.pptx'}

# 只存在於公開版、不從 SRC 覆蓋也不刪除的檔案
KEEP_PUBLIC_ONLY = {'buck-slides.css'}

TEXT_EXT = ('.md', '.py', '.css', '.json', '.txt')

# 順序有意義：長的路徑要先換
REPLACEMENTS = [
    (r'C:\Users\royal\.my-skills\skills', '<SKILLS_ROOT>'),
    (r'C:\Users\royal\.my-skills\docs\specs', '<REPO_ROOT>\\docs\\specs'),
    (r'C:\Users\royal\.my-skills', '<REPO_ROOT>'),
    (r'C:\Users\royal\OneDrive\桌面\碩士班', '<VAULT_ROOT>'),
    (r'C:\Users\royal\.claude', '<CLAUDE_HOME>'),
    (r'C:\Users\royal\Downloads', '<HOME>\\Downloads'),
    (r'C:\Users\royal', '<HOME>'),
    ('修課\\電源管理晶片設計與實作\\往年上課講義',
     '<VAULT_ROOT>\\<課程資料夾>\\<講義資料夾>'),
    ('修課\\電源管理晶片設計與實作\\電源管理晶片設計與實作(PMIC).md',
     '<課程資料夾>\\<課程MOC>.md'),
    ('碩士班\\', '<VAULT_ROOT>\\'),
    ('碩士班', '<VAULT_ROOT>'),
]

# 推之前這些字樣必須是 0 筆
BLACKLIST = ['royal', 'OneDrive', '碩士班', '電源管理晶片設計與實作', '羅宇佑']

# 公開版專屬修改：同步會用源版覆蓋，所以這些差異要在覆蓋後重新套上。
# 每筆 = (相對路徑, 要被取代的原文, 取代成什麼)。找不到原文 → 報 [PATCH-MISS] 並 exit 1
# （代表源版改寫過那一段，要回來更新這裡，不能默默漏掉）。
PUBLIC_PATCHES = [
    (
        'skills/handout-to-study/SKILL.md',
        '   - **不存在**：把本 skill 需要的樣式告知使用者，並在最終回報明講'
        '「版面 CSS 缺，Obsidian 會變成上下排列」＋啟用步驟。'
        '**不要自己去改 appearance.json 以外的 Obsidian 設定**。',
        '   - **不存在**：本 skill 資料夾附了一份 `buck-slides.css`，複製到 '
        '`<VAULT_ROOT>\\.obsidian\\snippets\\` 即可；接著請使用者到'
        '「設定 → 外觀 → CSS 程式片段」開啟 `buck-slides`。'
        '在最終回報明講這一步，否則 Obsidian 會變成上下排列。'
        '**不要自己去改 appearance.json 以外的 Obsidian 設定**。',
    ),
]


def patch_text(rel, text):
    """對單一檔案套上公開版專屬修改（寫檔前呼叫，確保內容一次到位）。"""
    rel = rel.replace(os.sep, '/')
    for prel, old, new in PUBLIC_PATCHES:
        if prel != rel:
            continue
        if new in text:
            continue
        if old in text:
            text = text.replace(old, new)
    return text


def depersonalize(text):
    for a, b in REPLACEMENTS:
        text = text.replace(a, b)
    return text.replace('<VAULT_ROOT>\\<VAULT_ROOT>', '<VAULT_ROOT>')


def sync():
    if not os.path.isdir(SRC):
        print('[ABORT] SRC_NOT_FOUND: ' + SRC)
        return 1

    for s in SKILLS:
        src_dir = os.path.join(SRC, s)
        dst_dir = os.path.join(DST, s)
        if not os.path.isdir(src_dir):
            print('[ABORT] SKILL_NOT_FOUND: ' + src_dir)
            return 1
        os.makedirs(dst_dir, exist_ok=True)

        src_names = set()
        for f in sorted(os.listdir(src_dir)):
            sp = os.path.join(src_dir, f)
            if not os.path.isfile(sp):
                continue
            if f in EXCLUDE_FILES:
                print('[SKIP] %s/%s（私人資產，不公開）' % (s, f))
                continue
            src_names.add(f)
            dp = os.path.join(dst_dir, f)
            if f.lower().endswith(TEXT_EXT):
                with open(sp, 'rb') as fh:
                    new = depersonalize(fh.read().decode('utf-8'))
                new = patch_text(os.path.relpath(dp, REPO), new)
                old = None
                if os.path.isfile(dp):
                    with open(dp, 'rb') as fh:
                        old = fh.read().decode('utf-8')
                if new != old:
                    with open(dp, 'w', encoding='utf-8', newline='\n') as fh:
                        fh.write(new)
                    print('[UPDATE] %s/%s' % (s, f))
            else:
                shutil.copy2(sp, dp)

        # 來源已刪除的檔案，公開版也要跟著刪（KEEP_PUBLIC_ONLY 除外）
        for f in sorted(os.listdir(dst_dir)):
            if f in src_names or f in KEEP_PUBLIC_ONLY or f in EXCLUDE_FILES:
                continue
            os.remove(os.path.join(dst_dir, f))
            print('[DELETE] %s/%s（來源已不存在）' % (s, f))

    return apply_patches()


def apply_patches():
    """重新套上公開版專屬修改（同步覆蓋後必跑）。"""
    miss = 0
    for rel, old, new in PUBLIC_PATCHES:
        p = os.path.join(REPO, rel.replace('/', os.sep))
        if not os.path.isfile(p):
            print('[PATCH-MISS] 檔案不存在：' + rel)
            miss += 1
            continue
        with open(p, 'rb') as fh:
            t = fh.read().decode('utf-8')
        if new in t:
            print('[PATCH-OK] 已套用：' + rel)
            continue
        if old not in t:
            print('[PATCH-MISS] %s 找不到要取代的原文——源版可能改寫過那一段，'
                  '回去更新 tools/sync.py 的 PUBLIC_PATCHES' % rel)
            miss += 1
            continue
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t.replace(old, new))
        print('[PATCH] 重新套用：' + rel)
    return 1 if miss else 0


def check():
    hits = 0
    for root, _, files in os.walk(DST):
        for f in files:
            if not f.lower().endswith(TEXT_EXT):
                continue
            p = os.path.join(root, f)
            with open(p, 'rb') as fh:
                t = fh.read().decode('utf-8', 'ignore')
            for w in BLACKLIST:
                for m in re.finditer(re.escape(w), t):
                    ln = t[:m.start()].count(chr(10)) + 1
                    print('[LEFTOVER] %s:%d  %s'
                          % (os.path.relpath(p, REPO), ln, w))
                    hits += 1
    print('[SUMMARY] leftovers=%d' % hits)
    return 1 if hits else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只檢查，不寫檔')
    a = ap.parse_args()

    if not a.check:
        rc = sync()
        if rc:
            return rc
        print()
    rc = check()
    if rc == 0:
        print('[DONE] 乾淨，可以 git add -A && git commit && git push')
    else:
        print('[FAIL] 有個資殘留，**先清乾淨再 push**')
    return rc


if __name__ == '__main__':
    sys.exit(main())
