# -*- coding: utf-8 -*-
"""handout-to-study Phase 7：從講義整頁 PNG 裁出內文/附錄要引用的圖。

CLI:  python crop_figs.py <來源img資料夾> <輸出資料夾> <jobs.json路徑>

jobs.json schema（陣列）:
  [
    {"src": "p37.png", "dst": "Ch9_p37_type1.png", "box": [0.03, 0.132, 0.99, 0.885]},
    {"src": "p38.png", "dst": "Ch9_p38_type2.png"}          <- box 省略時用 DEFAULT_BOX
  ]
  box = (left, top, right, bottom)，皆為佔整頁的比例（0~1）。

哨兵:  每張印 [CROP] <src> -> <dst> <px>；結尾 [DONE] cropped=<N>
exit:  0=全部成功；1=任一筆失敗（先印 [FAIL] src=<...>）
覆寫:  同名直接覆寫（冪等）

⚠️ DEFAULT_BOX 是 PMIC 課程投影片版式的實測值（去掉頁面標題列與頁尾校名列）。
   換課程／換版式一定要先目視確認一張，再批次跑。
⚠️ 跑完必目視抽查 max(2, 10%) 張：「印了 N 張成功」不證明裁對了。
"""
import json
import os
import sys

try:
    from PIL import Image
except ImportError:
    print('[FAIL] import PIL -> pip install pillow')
    sys.exit(1)

DEFAULT_BOX = (0.03, 0.132, 0.99, 0.885)


def main():
    if len(sys.argv) < 4:
        print('[FAIL] usage: python crop_figs.py <srcdir> <outdir> <jobs.json>')
        return 1

    src_dir, out_dir, jobs_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isdir(src_dir):
        print('[FAIL] SRCDIR_NOT_FOUND: ' + src_dir)
        return 1
    if not os.path.isfile(jobs_path):
        print('[FAIL] JOBS_NOT_FOUND: ' + jobs_path)
        return 1

    with open(jobs_path, 'rb') as fh:
        jobs = json.loads(fh.read().decode('utf-8'))

    os.makedirs(out_dir, exist_ok=True)

    ok = 0
    failed = 0
    for job in jobs:
        src = job.get('src')
        dst = job.get('dst')
        box = tuple(job.get('box', DEFAULT_BOX))
        sp = os.path.join(src_dir, src) if src else None
        if not src or not dst:
            failed += 1
            print('[FAIL] job missing src/dst: ' + repr(job))
            continue
        if not os.path.isfile(sp):
            failed += 1
            print('[FAIL] src=' + src + ' NOT_FOUND')
            continue
        try:
            im = Image.open(sp)
            w, h = im.size
            px = (int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))
            im.crop(px).save(os.path.join(out_dir, dst))
            ok += 1
            print('[CROP] ' + src + ' -> ' + dst + ' ' + str(px))
        except Exception as e:
            failed += 1
            print('[FAIL] src=' + src + ' ' + repr(e))

    if failed:
        print('[SUMMARY] cropped=' + str(ok) + ' failed=' + str(failed))
        return 1

    print('[DONE] cropped=' + str(ok))
    print('[REMINDER] 目視抽查 max(2, 10%) 張，確認沒把標題或別的圖框進去')
    return 0


if __name__ == '__main__':
    sys.exit(main())
