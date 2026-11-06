#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add figure embedding to the translation step of a locally adapted paper-to-study skill.

Usage:
    python3 update_env_kit.py [path/to/SKILL.md]

Default path: ~/.claude/skills/paper-to-study/SKILL.md
Safe to run twice. Keeps a backup in AI/SKILL.md.bak beside the skill.
Exit code: 0 = updated or already up to date; 1 = nothing written.
"""
import os
import shutil
import sys

MARK = '翻到哪放到哪'
QUOTE_LINE = '- 圖片引用保留：「如圖 X 所示」\n'
EMBED_LINE = (
    '- **嵌圖（翻到哪放到哪）**：翻到原文圖說時寫一行「（圖 N：圖說）」，每張圖嵌在該行正上方，'
    '照原文出現順序；`<img src="./Claude/img/<檔>.png" width="48%">`，(a)(b) 子圖兩張並排同一行、'
    '各 48%。圖檔用 Phase 1 擷取／匯入的同一批（figures.json 對應）。\n'
)
CHECK_OLD = '佔位字樣 0 筆。'
CHECK_NEW = '佔位字樣 0 筆；「（圖 N：」行數＝原文圖數，且每行正上方都有 `<img ... width="48%">`。'


def main():
    default = os.path.join('~', '.claude', 'skills', 'paper-to-study', 'SKILL.md')
    path = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else default)
    if not os.path.isfile(path):
        print('[ABORT] SKILL.md not found: ' + path)
        return 1
    with open(path, 'r', encoding='utf-8', newline='') as fh:
        raw = fh.read()
    if MARK in raw:
        print('[OK] already up to date: ' + path)
        return 0

    text = raw.replace('\r\n', '\n')
    start = text.find('## Phase 3')
    end = text.find('**Phase 3 自查點**', start)
    line_end = text.find('\n', end)
    if start < 0 or end < 0 or line_end < 0:
        print('[ABORT] Phase 3 section not found; nothing written')
        return 1
    if text.count(QUOTE_LINE, start, end) != 1 or text.count(CHECK_OLD, end, line_end) != 1:
        print('[ABORT] Phase 3 wording differs from the expected version; nothing written')
        return 1

    check = text[end:line_end].replace(CHECK_OLD, CHECK_NEW)
    body = text[start:end].replace(QUOTE_LINE, QUOTE_LINE + EMBED_LINE)
    new = text[:start] + body + check + text[line_end:]
    if '\r\n' in raw:
        new = new.replace('\n', '\r\n')

    backup_dir = os.path.join(os.path.dirname(path), 'AI')
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, 'SKILL.md.bak')
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(new)
    print('[DONE] translation figures added: ' + path)
    print('[BACKUP] ' + backup)
    return 0


if __name__ == '__main__':
    sys.exit(main())
