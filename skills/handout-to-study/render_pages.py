# -*- coding: utf-8 -*-
"""handout-to-study Phase 2：把講義 PDF 每一頁整頁 render 成 PNG。

CLI:  python render_pages.py <PDF絕對路徑> <輸出資料夾絕對路徑> [dpi]
輸出:  p01.png, p02.png, ...（總頁數 >=100 時改三位數 p001.png）
哨兵:  [DONE] rendered=<N> dir=<路徑>
exit:  0=全部成功；1=任一頁失敗（先印 [FAIL] page=<i>）
覆寫:  同名 PNG 直接覆寫，不備份（冪等）

規格：整頁 render、不做圖區剪裁（剪裁會配錯圖）。dpi 預設 150。
"""
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print('[FAIL] import fitz -> pip install pymupdf')
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print('[FAIL] usage: python render_pages.py <pdf> <outdir> [dpi]')
        return 1

    pdf_path = sys.argv[1]
    out_dir = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150

    if not os.path.isfile(pdf_path):
        print('[FAIL] PDF_NOT_FOUND: ' + pdf_path)
        return 1

    os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    if doc.is_encrypted:
        print('[FAIL] ENCRYPTED_PDF')
        return 1

    n = doc.page_count
    width = 3 if n >= 100 else 2
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    failed = 0
    for i in range(n):
        name = 'p' + str(i + 1).zfill(width) + '.png'
        dst = os.path.join(out_dir, name)
        try:
            pix = doc[i].get_pixmap(matrix=mat)
            pix.save(dst)
        except Exception as e:
            failed += 1
            print('[FAIL] page=' + str(i + 1) + ' ' + repr(e))

    doc.close()

    made = len([f for f in os.listdir(out_dir)
                if f.lower().endswith('.png') and f.startswith('p')])
    print('[INFO] page_count=' + str(n) + ' dpi=' + str(dpi) + ' png_in_dir=' + str(made))

    if failed:
        print('[SUMMARY] failed=' + str(failed))
        return 1

    print('[DONE] rendered=' + str(n) + ' dir=' + out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
