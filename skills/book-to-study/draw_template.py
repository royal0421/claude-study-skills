# -*- coding: utf-8 -*-
"""
draw_template.py — book-to-study 自繪輔助圖範本
（2026-07-07 複製自 Ch1 黃金樣本 AI\\_draw4.py，原檔唯讀未動）

給執行 skill 的模型的使用說明：
1. 把本檔複製到 <章節資料夾>\\AI\\_draw.py 再改寫；勿直接在 skill 資料夾內執行。
2. 「框架函式區」（setup / meas / fit / node / arrow）原樣沿用——它已解決
   CJK 字型載入與「文字自動縮字級塞進固定寬度框」兩個坑，勿重造輪子。
3. 「圖內容區」（====== 分隔的 1)~4) 段）是 Ch1 的四張圖，只供結構參考——
   每章依 AI\\_aux_todo.md 清單全部重寫；圖面保留「（輔助圖，非原書圖）」標註慣例。
4. ⚠ OUT 目前是相對路徑 'AI/figures'，對執行 cwd 敏感——改寫時一律把 OUT 改成
   該章 figures 的**絕對路徑**（如 r'C:\\...\\Ch2 System Level Test Methods\\AI\\figures'）。
5. 跑完逐張用 Read 工具讀圖驗證（文字沒溢框、內容正確），再回填筆記引用。
依賴：matplotlib（本 skill 的軟依賴：缺了跳過自繪走文字降級，見 SKILL.md 失敗路徑表）。
預期修訂區：使用者對 Ch1 方塊圖視覺風格不甚滿意——本範本風格日後可能由 Opus
與使用者迭代改寫；屆時修訂 SKILL.md 對應節並同步更新本檔。
"""
# ============ 以下為 Ch1 AI\_draw4.py 原文（僅供參考結構） ============
"""重繪自繪方塊圖：fixed-width 框自動放大字級填滿框寬；auto-width 框整體加大字。"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager
import numpy as np
import os

cjk = None
for c in [r'C:\Windows\Fonts\msjh.ttc', r'C:\Windows\Fonts\msjhbd.ttc', r'C:\Windows\Fonts\mingliu.ttc']:
    if os.path.exists(c):
        cjk = c; break
fp = font_manager.FontProperties(fname=cjk)
fpb = font_manager.FontProperties(fname=cjk, weight='bold')
plt.rcParams['axes.unicode_minus'] = False
OUT = 'AI/figures'
LS = 1.42
PADX, PADT, PADB, GAP = 2.6, 2.4, 2.4, 1.8

def setup(w_in, h_in):
    fig, ax = plt.subplots(figsize=(w_in, h_in), dpi=170)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')
    fig.canvas.draw()
    return fig, ax

def meas(fig, ax, s, fobj, fs):
    if not s:
        return 0.0, 0.0
    t = ax.text(50, 50, s, fontproperties=fobj, fontsize=fs, linespacing=LS)
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    inv = ax.transData.inverted()
    p0 = inv.transform((bb.x0, bb.y0)); p1 = inv.transform((bb.x1, bb.y1))
    t.remove()
    return abs(p1[0] - p0[0]), abs(p1[1] - p0[1])

def fit(fig, ax, s, fobj, target_w, start, lo=9):
    fs = start
    while fs > lo:
        w, _ = meas(fig, ax, s, fobj, fs)
        if w <= target_w:
            return fs
        fs -= 0.5
    return lo

def node(fig, ax, cx, top, title, lines, fc, ec='#3a3a3a', tc='#111',
         fixed_w=None, align='center', body_fs=16, title_fs=18, fill=0.95):
    body = '\n'.join(lines) if lines else ''
    if fixed_w is not None:
        avail = (fixed_w - 2 * PADX) * fill
        if body:
            body_fs = fit(fig, ax, body, fp, avail, start=body_fs)
        if title:
            title_fs = fit(fig, ax, title, fpb, avail, start=title_fs)
        w = fixed_w
    tw, th = meas(fig, ax, title, fpb, title_fs)
    bw, bh = meas(fig, ax, body, fp, body_fs)
    if fixed_w is None:
        w = max(tw, bw) + 2 * PADX
    h = PADT + th + (GAP if (title and body) else 0) + bh + PADB
    x0 = cx - w / 2; y0 = top - h
    ax.add_patch(FancyBboxPatch((x0 + 0.5, y0 + 0.5), w - 1.0, h - 1.0,
                 boxstyle="round,pad=0.5,rounding_size=2.4", lw=2.1, edgecolor=ec, facecolor=fc))
    yy = top - PADT
    if title:
        ax.text(cx, yy, title, ha='center', va='top', fontproperties=fpb, fontsize=title_fs, color=tc)
        yy -= (th + GAP)
    if body:
        if align == 'center':
            ax.text(cx, yy, body, ha='center', va='top', fontproperties=fp, fontsize=body_fs, color='#1c1c1c', linespacing=LS)
        else:
            ax.text(x0 + PADX, yy, body, ha='left', va='top', fontproperties=fp, fontsize=body_fs, color='#1c1c1c', linespacing=LS)
    return dict(l=x0, r=x0 + w, t=top, b=y0, cx=cx, cy=(top + y0) / 2, w=w, h=h)

def arrow(ax, p1, p2, lab='', col='#555', lw=2.6, labdx=0, labdy=0, labcol=None):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=24, lw=lw, color=col, shrinkA=3, shrinkB=3))
    if lab:
        ax.text((p1[0] + p2[0]) / 2 + labdx, (p1[1] + p2[1]) / 2 + labdy, lab, ha='center', va='center',
                fontproperties=fpb, fontsize=15, color=labcol or col, bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))

# ===================== 1) 全章地圖（動態垂直堆疊）=====================
fig, ax = setup(13.5, 11.5)
ax.text(50, 99, 'Ch1 System Level ESD Design — 全章地圖', ha='center', va='top', fontproperties=fpb, fontsize=20, color='#0b2e59')
y = 94.5; W = 96
gt = node(fig, ax, 50, y, '黃金主線（精隨）',
          ['ESD 保護 = 一條「平時隱形、ESD 時現身」的電流路徑',
           '矛盾：保護夠強  <->  不傷訊號 / 面積 / latch-up',
           '→ 走向 co-design ＋ 用模擬預測'],
          '#fff4d6', ec='#d4a017', tc='#7a5a00', fixed_w=W, align='center', body_fs=17, title_fs=19)
y = gt['b'] - 2.4
f11 = node(fig, ax, 50, y, '【框架】1.1 理解 ESD：為何系統級是新戰場',
           ['ESD = 衰減電流脈衝（ns 級、可達數十 A）',
            'component（斷電）  vs  system（通電、30 kV）',
            '關鍵：component 過 ≠ system 安全'],
           '#e8f0fb', ec='#2b6cb0', tc='#143e6e', fixed_w=W, align='center', body_fs=17, title_fs=19)
y = f11['b'] - 3.0
pL = node(fig, ax, 25.5, y, '【支柱一】1.2 On-Chip',
          ['• design window（Vh<Vop→latch-up）', '• rail-based / local clamp',
           '• two-stage（Rs·Ci 濾 CDM）', '• 內部電路（regulator/DC-DC）', '• 多電壓域 back-to-back diode'],
          '#e7f6ec', ec='#2f855a', tc='#1c5239', fixed_w=47, align='left', body_fs=15, title_fs=17)
pR = node(fig, ax, 74.5, y, '【支柱二】1.3 Off-Chip',
          ['• SoC/SiP 抹掉 component/system 界線', '• Si TVS（最佳）vs varistor/polymer',
           '• signal integrity <-> 電容 矛盾', '• TVS 緊貼 connector', '• 用 trace 電感衰減 overshoot'],
          '#fdeee8', ec='#c05621', tc='#8a3a12', fixed_w=47, align='left', body_fs=15, title_fs=17)
ax.text(50, (pL['t'] + pL['b']) / 2, '<->\nco-\ndesign', ha='center', va='center', fontproperties=fpb, fontsize=14, color='#9a3412')
y = min(pL['b'], pR['b']) - 3.0
tool = node(fig, ax, 50, y, '【工具】1.4–1.5 用模擬預測 ESD',
            ['compact model = 標準元件 ＋ 寄生 BJT ＋ avalanche 源',
             'mixed-mode（電路＋FEM 同矩陣共解）→ DECIMM 即時參數化'],
            '#efe9f7', ec='#6b46c1', tc='#44308a', fixed_w=W, align='center', body_fs=17, title_fs=19)
arrow(ax, (50, f11['b']), (50, max(pL['t'], pR['t']) + 0.3), col='#888')
arrow(ax, (pL['cx'], pL['b']), (45, tool['t']), col='#888')
arrow(ax, (pR['cx'], pR['b']), (55, tool['t']), col='#888')
plt.tight_layout(); plt.savefig(OUT + '/aux-chapter-map.png', bbox_inches='tight'); plt.close()
print('map done', round(tool['b'], 1))

# ===================== 2) 三層防線 =====================
fig, ax = setup(15.5, 7.2)
ax.text(50, 96, 'ESD 的三層防線（電流逐層分流）', ha='center', va='top', fontproperties=fpb, fontsize=19, color='#0b2e59')
stages = [
    (10, 'ESD 源', ['cable / 人', '可達 30 kV', '峰值 ~30 A'], '#fbeaea', '#b03030', '#7a1f1f'),
    (30, '① 系統 port', ['connector', 'chassis GND', '(=ESDMINUS)'], '#fff4d6', '#d4a017', '#7a5a00'),
    (50, '② 板級', ['TVS 分掉', '大部分電流', '+ ferrite 濾'], '#fdeee8', '#c05621', '#8a3a12'),
    (70, '③ on-chip', ['clamp/diode', '擋 secondary', '殘餘電流'], '#e7f6ec', '#2f855a', '#1c5239'),
    (90, '內部電路', ['→ 安全', '夾在安全', '電壓下'], '#e8f0fb', '#2b6cb0', '#143e6e'),
]
rects = []
for x, t, b, fc, ec, tc in stages:
    rects.append(node(fig, ax, x, 74, t, b, fc, ec=ec, tc=tc, body_fs=16, title_fs=18, align='center'))
for i in range(len(rects) - 1):
    arrow(ax, (rects[i]['r'], rects[i]['cy']), (rects[i + 1]['l'], rects[i + 1]['cy']), col='#555', lw=max(2.0, 6.5 - i))
ax.text(50, 30, '電流大部分在「②板級 TVS」就分流到地；只剩殘餘 secondary current 進到 ③on-chip——', ha='center', va='top', fontproperties=fp, fontsize=14.5, color='#333')
ax.text(50, 24.5, '但殘餘仍比標準 component（HBM/MM/CDM）高一個數量級，故對外 pin 要特別設計。', ha='center', va='top', fontproperties=fp, fontsize=14.5, color='#333')
plt.tight_layout(); plt.savefig(OUT + '/aux-three-lines-defense.png', bbox_inches='tight'); plt.close()
print('three-lines done')

# ===================== 3) 決策樹：on-chip =====================
fig, ax = setup(13.5, 12.5)
ax.text(50, 99, '決策樹：on-chip 選 rail-based 還是 local clamp？', ha='center', va='top', fontproperties=fpb, fontsize=19, color='#0b2e59')
ax.text(50, 94.6, '（輔助圖，非原書圖）', ha='center', va='top', fontproperties=fp, fontsize=13, color='#666')
start = node(fig, ax, 50, 92, '要保護一個 on-chip pin', [], '#e8f0fb', ec='#2b6cb0', tc='#143e6e', title_fs=19)
q1 = node(fig, ax, 50, 81.5, 'Q1：pin 屬於下列任一？',
          ['• 高壓容忍 / 雙向 (dual-direction)', '• back-drive / 通電下扛系統級'],
          '#fff4d6', ec='#d4a017', tc='#7a5a00', body_fs=17, title_fs=19, align='left')
local = node(fig, ax, 77, 62, '→ LOCAL CLAMP',
             ['每 pin 一顆 dedicated', '雙向 / 高壓 OK、波形好估', '（較佔面積、製程敏感）'],
             '#fdeee8', ec='#c05621', tc='#8a3a12', body_fs=17, title_fs=19, align='center')
q2 = node(fig, ax, 26, 59, 'Q2：pin 多 / 面積敏感？', [], '#fff4d6', ec='#d4a017', tc='#7a5a00', title_fs=19)
rail = node(fig, ax, 17, 40, '→ RAIL-BASED',
            ['diode + rail + core clamp', '省面積、適合多 pin / SoC', '（受 bus 電阻 / sneak path）'],
            '#e7f6ec', ec='#2f855a', tc='#1c5239', body_fs=16.5, title_fs=19, align='center')
both = node(fig, ax, 55, 40, '→ 兩者皆可', ['少 pin 常用 local', '（可攜、SPICE 可設計）'],
            '#eef2f4', ec='#556677', tc='#334455', body_fs=17, title_fs=19, align='center')
notes = node(fig, ax, 50, 21, '※ 三個必記附帶條件',
             ['1. snapback：Vh > Vop，否則 latch-up（SCR 最危險）',
              '2. CDM 短脈衝：加 two-stage（Rs·Ci 濾、Rs=(Vp-Vi)/Ic2）',
              '3. 通電系統級：active clamp 失效 → 改 anti-parallel diode 或 local'],
             '#fbeaea', ec='#b03030', tc='#7a1f1f', fixed_w=92, align='left', body_fs=17, title_fs=19)
arrow(ax, (50, start['b']), (50, q1['t']))
arrow(ax, (q1['r'], q1['cy'] + 2), (local['cx'], local['t']), '是', col='#c05621', labdx=3, labdy=1)
arrow(ax, (41, q1['b']), (q2['cx'] + 5, q2['t']), '否', col='#2b6cb0', labdx=-3)
arrow(ax, (21, q2['b']), (rail['cx'], rail['t']), '是', col='#2f855a', labdx=-3)
arrow(ax, (45, q2['b']), (both['cx'], both['t']), '否（少 pin）', col='#556677', labdx=10)
plt.tight_layout(); plt.savefig(OUT + '/aux-decision-onchip.png', bbox_inches='tight'); plt.close()
print('onchip done', round(notes['b'], 1))

# ===================== 4) 決策樹：off-chip =====================
fig, ax = setup(14.5, 10.0)
ax.text(50, 99, '決策樹：off-chip 抑制元件怎麼選？', ha='center', va='top', fontproperties=fpb, fontsize=19, color='#0b2e59')
ax.text(50, 94.6, '（輔助圖，非原書圖）', ha='center', va='top', fontproperties=fp, fontsize=13, color='#666')
start = node(fig, ax, 50, 92, '要保護的線 / 應用是哪種？', [], '#e8f0fb', ec='#2b6cb0', tc='#143e6e', title_fs=19)
b1 = node(fig, ax, 18, 80, '高速資料線', ['USB / HDMI / GbE', '(>100 Mbps)'], '#fff4d6', ec='#d4a017', tc='#7a5a00', body_fs=15.5, title_fs=18)
b2 = node(fig, ax, 50, 80, '低頻 / 類比 / 電源', ['音訊、感測、供電'], '#fff4d6', ec='#d4a017', tc='#7a5a00', body_fs=15.5, title_fs=18)
b3 = node(fig, ax, 82, 80, '極高壓 / 雷擊級', ['數百 V 容忍'], '#fff4d6', ec='#d4a017', tc='#7a5a00', body_fs=15.5, title_fs=18)
o1 = node(fig, ax, 18, 59, '→ 低電容 Si TVS', ['~0.1 pF、clamp 8–15 V', '低 Ron、turn-on <1 ns', '× 大電容會濾掉訊號'],
          '#e7f6ec', ec='#2f855a', tc='#1c5239', body_fs=15.5, title_fs=18)
o2 = node(fig, ax, 50, 59, '→ TVS / 高電容 TVS', ['可用較高電容', '與 trace 電感成低通', '兼濾 EMI；+ ferrite'],
          '#eef6ee', ec='#2f855a', tc='#1c5239', body_fs=15.5, title_fs=18)
o3 = node(fig, ax, 82, 59, '→ varistor / spark gap', ['clamp 高 150–500 V', '慢、~10–20 zap 退化', 'surge robustness 高'],
          '#fdeee8', ec='#c05621', tc='#8a3a12', body_fs=15.5, title_fs=18)
key = node(fig, ax, 50, 33, '共通關鍵',
           ['• clamp 量級：Si TVS 8–15 V  <<  varistor / polymer 150–500 V（差一個數量級）',
            '• 選 TVS 看「ESD 時域 clamping 波形（含 overshoot）」，非 datasheet kV 或 8/20 µs surge',
            '• 擺位：緊貼 connector；L2（TVS→IC）長→好、L3（訊號線→TVS）短→好；參考 chassis GND'],
           '#eaf1f7', ec='#2b6cb0', tc='#143e6e', fixed_w=94, align='left', body_fs=17, title_fs=19)
arrow(ax, (42, start['b']), (b1['cx'], b1['t']))
arrow(ax, (50, start['b']), (b2['cx'], b2['t']))
arrow(ax, (58, start['b']), (b3['cx'], b3['t']))
arrow(ax, (b1['cx'], b1['b']), (o1['cx'], o1['t']))
arrow(ax, (b2['cx'], b2['b']), (o2['cx'], o2['t']))
arrow(ax, (b3['cx'], b3['b']), (o3['cx'], o3['t']))
plt.tight_layout(); plt.savefig(OUT + '/aux-decision-offchip.png', bbox_inches='tight'); plt.close()
print('offchip done', round(key['b'], 1))
print('ALL DONE')
