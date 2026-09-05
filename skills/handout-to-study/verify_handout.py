# -*- coding: utf-8 -*-
"""handout-to-study Phase 9：兩份 md 的格式驗證（唯讀，不改任何檔案）。

CLI:  python verify_handout.py <逐頁講解md> <重點複習md> <img資料夾> <總頁數N>
輸出:  逐條 [PASS]/[WARN]/[ERROR]；結尾 [SUMMARY] errors=<E> warnings=<W>
exit:  0 = errors==0；1 = 有 error（warnings 不擋關，但要逐條看過）

檢查項（對應 SKILL.md 的 V1~V10）：
  V1  圖片引用集合 = 1..N，無缺無重                       ERROR
  V2  每個 mermaid 節點（以行為單位）的 $$ 數量 ∈ {0,2}    ERROR
  V3  callout 區塊內無「裸空行」                           ERROR
  V4  <summary>/<sub> 內容不含 $ 或 **                     ERROR
  V5  全檔無「實機」                                       ERROR
  V6  無佔位字樣 待補 / TODO / [範例 / XXX                 ERROR
  V7  frontmatter 有 cssclasses = buck-slides / buck-review ERROR
  V8  並排表格（含 ![]( 的列）表頭與分隔列都是兩欄          ERROR
  V9  重點複習含 §1~§11                                    WARN
  V10 鏈狀 mermaid 卻用 graph TD（應改 LR）                 WARN
"""
import os
import re
import sys

ERRORS = []
WARNS = []
PASSES = []


def err(msg):
    ERRORS.append(msg)
    print('[ERROR] ' + msg)


def warn(msg):
    WARNS.append(msg)
    print('[WARN] ' + msg)


def ok(msg):
    PASSES.append(msg)
    print('[PASS] ' + msg)


def read(path):
    with open(path, 'rb') as fh:
        return fh.read().decode('utf-8')


def node_labels(line):
    """抽出一行 mermaid 裡的每個節點標籤內容（含引號）。

    支援同一行多個節點（A[...] --> B["..."]）、巢狀大括號（\\frac{1}{2}）、
    以及 A(("...")) 這類複合形狀。找不到節點就回空 list。
    """
    openers = {'[': ']', '(': ')', '{': '}'}
    out = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch in openers and i > 0 and (line[i - 1].isalnum() or line[i - 1] == '_'):
            close = openers[ch]
            depth, j, inq = 0, i, False
            while j < n:
                c = line[j]
                if c == '"':
                    inq = not inq
                elif not inq:
                    if c == ch:
                        depth += 1
                    elif c == close:
                        depth -= 1
                        if depth == 0:
                            break
                j += 1
            out.append(line[i + 1:j])
            i = j + 1
            continue
        i += 1
    return out


def mermaid_blocks(text):
    """回傳 list of (起始行號, [行, ...])。"""
    out = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('```mermaid'):
            start = i
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                body.append(lines[i])
                i += 1
            out.append((start + 1, body))
        i += 1
    return out


# ---------------- V1 ----------------
def v1_images(text, img_dir, n, label):
    refs = re.findall(r'!\[\]\([^)]*?/p(\d+)\.png\)', text)
    nums = [int(x) for x in refs]
    want = set(range(1, n + 1))
    got = set(nums)
    dup = [x for x in got if nums.count(x) > 1]
    if got != want:
        missing = sorted(want - got)
        extra = sorted(got - want)
        err('V1 %s 圖片引用不等於 1..%d：缺 %s；多 %s' % (label, n, missing, extra))
    elif dup:
        err('V1 %s 圖片重複引用：%s' % (label, sorted(dup)))
    else:
        ok('V1 %s 圖片引用 1..%d 完整無重複' % (label, n))

    if img_dir and os.path.isdir(img_dir):
        pngs = [f for f in os.listdir(img_dir)
                if f.lower().endswith('.png') and f.startswith('p')]
        if len(pngs) != n:
            err('V1b img 資料夾 PNG 數 %d != 總頁數 %d（%s）' % (len(pngs), n, img_dir))
        else:
            ok('V1b img 資料夾 PNG 數 = %d' % n)


# ---------------- V2 / V10 ----------------
def v2_v10_mermaid(text, label):
    bad = []
    chain_td = []
    for start, body in mermaid_blocks(text):
        header = body[0].strip() if body else ''
        for off, line in enumerate(body):
            ln = start + off + 1
            labels = node_labels(line)
            if not labels:
                c = line.count('$$')
                if c not in (0, 2):
                    bad.append((ln, c, line.strip()[:60]))
                continue
            for lab in labels:
                c = lab.count('$$')
                s = lab.strip()
                # R10a：標籤含 $$ 就必須用雙引號包住，否則 Obsidian 會壞
                if c and not (s.startswith('"') and s.endswith('"')):
                    bad.append((ln, c, '節點含 $$ 卻沒用雙引號包住（違反 R10a）：' + s[:45]))
                    continue
                if c not in (0, 2):
                    bad.append((ln, c, s[:60]))
        # V10：鏈狀判定
        edges = []
        for line in body:
            for m in re.finditer(r'([A-Za-z0-9_]+)\s*-->', line):
                edges.append(m.group(1))
        arrows = sum(line.count('-->') for line in body)
        nodes = set()
        for line in body:
            for m in re.finditer(r'\b([A-Za-z][A-Za-z0-9_]*)\s*[\[\(\{]', line):
                nodes.add(m.group(1))
        if ('TD' in header or 'TB' in header) and len(nodes) >= 4 and arrows == len(nodes) - 1:
            outdeg = {}
            for s in edges:
                outdeg[s] = outdeg.get(s, 0) + 1
            if outdeg and max(outdeg.values()) == 1:
                chain_td.append(start)

    if bad:
        for ln, c, snippet in bad:
            err('V2 %s 第 %d 行的 mermaid 節點有 %d 個 $$（必須是 0 或 2）：%s'
                % (label, ln, c, snippet))
    else:
        ok('V2 %s 所有 mermaid 節點的 $$ 數量合法' % label)

    for ln in chain_td:
        warn('V10 %s 第 %d 行起的 mermaid 疑似鏈狀卻用 TD，建議改 graph LR（R13）'
             % (label, ln))
    if not chain_td:
        ok('V10 %s 無「鏈狀圖用 TD」的疑慮' % label)


# ---------------- V3 ----------------
def v3_callout(text, label):
    lines = text.split('\n')
    problems = []
    i = 0
    while i < len(lines):
        if re.match(r'^>\s*\[!', lines[i]):
            j = i + 1
            while j < len(lines):
                cur = lines[j]
                if cur.startswith('>'):
                    j += 1
                    continue
                if cur.strip() == '':
                    k = j + 1
                    while k < len(lines) and lines[k].strip() == '':
                        k += 1
                    # 下一段若是「新的 callout 標頭」，這個空行是兩個 callout 之間的正常分隔
                    if (k < len(lines) and lines[k].startswith('>')
                            and not re.match(r'^>\s*\[!', lines[k])):
                        problems.append(j + 1)
                        j = k
                        continue
                break
            i = j
        else:
            i += 1
    if problems:
        for ln in problems:
            err('V3 %s 第 %d 行是 callout 內的裸空行（要寫成單獨一個 >）' % (label, ln))
    else:
        ok('V3 %s callout 區塊無裸空行' % label)


# ---------------- V4 ----------------
def v4_html_tags(text, label):
    bad = []
    for tag in ('summary', 'sub'):
        for m in re.finditer(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), text, re.S):
            content = m.group(1)
            if '$' in content or '**' in content:
                ln = text[:m.start()].count('\n') + 1
                bad.append((tag, ln, content.strip()[:60]))
    if bad:
        for tag, ln, snippet in bad:
            err('V4 %s 第 %d 行 <%s> 內含 $ 或 **（HTML 標籤內不解析 LaTeX/markdown）：%s'
                % (label, ln, tag, snippet))
    else:
        ok('V4 %s <summary>/<sub> 內無 $ 或 **' % label)


# ---------------- V5 / V6 ----------------
def v5_v6_words(text, label):
    if '實機' in text:
        for m in re.finditer('實機', text):
            ln = text[:m.start()].count('\n') + 1
            err('V5 %s 第 %d 行出現「實機」（應為「實際」）' % (label, ln))
    else:
        ok('V5 %s 無「實機」' % label)

    hits = []
    for pat in ('待補', 'TODO', '[範例', 'XXX'):
        for m in re.finditer(re.escape(pat), text):
            ln = text[:m.start()].count('\n') + 1
            hits.append((pat, ln))
    if hits:
        for pat, ln in hits:
            err('V6 %s 第 %d 行有佔位字樣「%s」' % (label, ln, pat))
    else:
        ok('V6 %s 無佔位字樣' % label)


# ---------------- V7 ----------------
def v7_frontmatter(text, label, expect):
    head = text.split('---')
    if not text.startswith('---') or len(head) < 3:
        err('V7 %s 沒有 frontmatter' % label)
        return
    fm = head[1]
    if 'cssclasses' not in fm:
        err('V7 %s frontmatter 缺 cssclasses' % label)
    elif expect not in fm:
        err('V7 %s frontmatter 的 cssclasses 應為 %s' % (label, expect))
    else:
        ok('V7 %s cssclasses = %s' % (label, expect))


# ---------------- V8 ----------------
def cells(line):
    s = line.strip()
    if not s.startswith('|'):
        return None
    return len(s.strip('|').split('|'))


def v8_slide_tables(text, label):
    lines = text.split('\n')
    bad = []
    for i, line in enumerate(lines):
        if '![](' not in line or not line.strip().startswith('|'):
            continue
        c = cells(line)
        if c != 2:
            bad.append((i + 1, '圖片列 %s 欄' % c))
            continue
        if i >= 2:
            hdr, sep = cells(lines[i - 2]), cells(lines[i - 1])
            if hdr != 2 or sep != 2:
                bad.append((i + 1, '表頭 %s 欄 / 分隔列 %s 欄' % (hdr, sep)))
        else:
            bad.append((i + 1, '圖片表格上方缺表頭與分隔列'))
    if bad:
        for ln, why in bad:
            err('V8 %s 第 %d 行的並排表格不是兩欄：%s' % (label, ln, why))
    else:
        ok('V8 %s 並排表格皆為兩欄' % label)


# ---------------- V9 ----------------
def v9_sections(text, label):
    found = set(int(x) for x in re.findall(r'§\s*(\d+)', text))
    missing = sorted(set(range(1, 12)) - found)
    if missing:
        warn('V9 %s 缺少節次 §%s' % (label, '、§'.join(str(x) for x in missing)))
    else:
        ok('V9 %s §1~§11 齊全' % label)


def main():
    if len(sys.argv) < 5:
        print('[ERROR] usage: python verify_handout.py <逐頁講解md> <重點複習md> <img夾> <N>')
        return 1

    slides_md, review_md, img_dir, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

    for p in (slides_md, review_md):
        if not os.path.isfile(p):
            print('[ERROR] FILE_NOT_FOUND: ' + p)
            return 1

    s = read(slides_md)
    r = read(review_md)

    print('=== 逐頁講解 ===')
    v1_images(s, img_dir, n, '逐頁講解')
    v2_v10_mermaid(s, '逐頁講解')
    v3_callout(s, '逐頁講解')
    v4_html_tags(s, '逐頁講解')
    v5_v6_words(s, '逐頁講解')
    v7_frontmatter(s, '逐頁講解', 'buck-slides')
    v8_slide_tables(s, '逐頁講解')

    print('=== 重點複習 ===')
    v2_v10_mermaid(r, '重點複習')
    v3_callout(r, '重點複習')
    v4_html_tags(r, '重點複習')
    v5_v6_words(r, '重點複習')
    v7_frontmatter(r, '重點複習', 'buck-review')
    v8_slide_tables(r, '重點複習')
    v9_sections(r, '重點複習')

    print('[SUMMARY] errors=%d warnings=%d' % (len(ERRORS), len(WARNS)))
    return 1 if ERRORS else 0


if __name__ == '__main__':
    sys.exit(main())
