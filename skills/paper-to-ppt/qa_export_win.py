# -*- coding: utf-8 -*-
"""PowerPoint COM（late binding，不靠 type library）把每張投影片匯出 1280x960 JPEG。
用法：python qa_export_win.py <PPT.pptx> <outdir>
只關本次新開的 PowerPoint；呼叫前已有 PowerPoint 在跑就只關本次開的簡報。"""
import os
import sys

import pythoncom
import win32com.client.dynamic


def main(pptx, outdir):
    pptx, outdir = os.path.abspath(pptx), os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    pythoncom.CoInitialize()
    try:
        running = True
        try:
            app = win32com.client.dynamic.Dispatch(pythoncom.GetActiveObject("PowerPoint.Application")
                                                   .QueryInterface(pythoncom.IID_IDispatch))
        except pythoncom.com_error:
            running = False
            app = win32com.client.dynamic.Dispatch("PowerPoint.Application")
        prs = app.Presentations.Open(pptx, True, False, False)  # ReadOnly, Untitled=False, WithWindow=False
        try:
            n = prs.Slides.Count
            for i in range(1, n + 1):
                prs.Slides.Item(i).Export(os.path.join(outdir, "slide-%02d.jpg" % i), "JPG", 1280, 960)
            print("exported %d slides -> %s" % (n, outdir))
        finally:
            prs.Close()
            if not running:
                app.Quit()
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    main(*sys.argv[1:3])
