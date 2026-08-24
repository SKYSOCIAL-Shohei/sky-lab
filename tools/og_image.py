#!/usr/bin/env python3
"""
記事の見出し画像

写真ではなく、絵の具のマーブル（アクリルポア）のような抽象アートで
記事のテーマを表す。濃淡の異なる色の流れが画面を覆い、白い抜け・
気泡・金の脈が質感を作る。その中に、渡されていない決裁を表す
小さな朱の光がひとつだけ灯る。静かな直線と円（テックの気配）を
最小限だけ添える。タイトルの文字は入れない。

pillar（構築記録／収集と考察）によって色調だけを切り替える。
構図そのものは全記事で共通（同じ様式の記録が積み重なっていく、
という意図的な選択）。

Playwrightで実際に描画してスクリーンショットし、1200x630のPNGにする。

  使い方:  python3 tools/og_image.py 012 構築記録 R-0015
  出力:    articles/og/012.png
"""
import os, sys
from playwright.sync_api import sync_playwright

# (メイン色, 濃色, テック線色) の3色セット
PILLAR_PALETTE = {
    "構築記録":   ("#2C4A6E", "#1A335A", "#4A6FA0"),
    "収集と考察": ("#6E5330", "#4A3820", "#8A7050"),
}

TPL = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  *{{margin:0;padding:0}}
  html,body{{width:1200px;height:630px;overflow:hidden;background:#F6F3EC}}
</style></head>
<body>
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="marble" x="-30%" y="-30%" width="160%" height="160%">
      <feTurbulence type="fractalNoise" baseFrequency="0.008 0.014" numOctaves="5" seed="{seed1}" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="90"/>
    </filter>
    <filter id="marble2" x="-30%" y="-30%" width="160%" height="160%">
      <feTurbulence type="fractalNoise" baseFrequency="0.02 0.03" numOctaves="4" seed="{seed2}" result="n2"/>
      <feDisplacementMap in="SourceGraphic" in2="n2" scale="34"/>
    </filter>
    <filter id="stroke" x="-30%" y="-30%" width="160%" height="160%">
      <feTurbulence type="fractalNoise" baseFrequency="0.015 0.05" numOctaves="3" seed="{seed3}" result="n3"/>
      <feDisplacementMap in="SourceGraphic" in2="n3" scale="14"/>
    </filter>
    <filter id="grain">
      <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="5" result="g"/>
      <feColorMatrix in="g" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.05 0"/>
    </filter>
  </defs>

  <rect width="1200" height="630" fill="#F6F3EC"/>

  <!-- 絵の具の大きな流れ。濃淡の異なる色を重ねてマーブル状にする -->
  <g filter="url(#marble)">
    <path d="M -50 630 C 80 380, 60 180, 260 40 C 420 -60, 560 60, 520 220
             C 480 380, 620 440, 780 380 C 920 330, 980 440, 900 560
             C 840 650, 500 640, 260 630 Z" fill="{main}" opacity="0.92"/>
    <path d="M -50 630 C 120 460, 140 300, 320 190 C 460 110, 520 200, 460 300
             C 400 400, 480 470, 620 430 C 720 400, 760 480, 680 560
             C 600 630, 300 640, 40 630 Z" fill="{dark}" opacity="0.55"/>
  </g>

  <!-- 白い抜け（マーブルの割れ目） -->
  <g filter="url(#marble2)" opacity="0.9">
    <path d="M 40 520 C 140 460, 160 360, 260 320 C 320 296, 340 340, 300 380 C 250 430, 200 480, 120 540 Z" fill="#F6F3EC"/>
    <path d="M 300 120 C 380 90, 440 130, 420 190 C 400 240, 340 240, 320 190 C 306 156, 290 140, 300 120 Z" fill="#F6F3EC" opacity="0.85"/>
    <path d="M 560 260 C 640 240, 700 290, 660 340 C 630 376, 570 360, 560 320 C 554 296, 550 276, 560 260 Z" fill="#F6F3EC" opacity="0.7"/>
  </g>

  <!-- 気泡（アクリルポアの質感） -->
  <g filter="url(#marble2)" opacity="0.85">
    <circle cx="210" cy="150" r="46" fill="none" stroke="#F6F3EC" stroke-width="3" opacity="0.55"/>
    <circle cx="150" cy="300" r="70" fill="none" stroke="#F6F3EC" stroke-width="2.5" opacity="0.4"/>
    <circle cx="640" cy="330" r="34" fill="none" stroke="#F6F3EC" stroke-width="2" opacity="0.5"/>
    <circle cx="440" cy="90" r="12" fill="#F6F3EC" opacity="0.5"/>
    <circle cx="780" cy="470" r="22" fill="none" stroke="#F6F3EC" stroke-width="2" opacity="0.4"/>
  </g>

  <!-- 金の脈 -->
  <g filter="url(#stroke)" opacity="0.85">
    <path d="M 40 560 C 200 460, 220 320, 160 200 C 130 130, 220 60, 340 70" fill="none" stroke="#C9A24B" stroke-width="2.5"/>
    <path d="M 520 240 C 600 220, 660 280, 700 360 C 730 420, 800 430, 860 390" fill="none" stroke="#C9A24B" stroke-width="2"/>
  </g>

  <!-- 筆致 -->
  <g filter="url(#stroke)" opacity="0.5">
    <path d="M 700 80 C 760 120, 820 100, 900 140" fill="none" stroke="#1A1D24" stroke-width="5" stroke-linecap="round"/>
    <path d="M 940 460 C 1000 420, 1040 460, 1100 430" fill="none" stroke="#1A1D24" stroke-width="3" stroke-linecap="round"/>
  </g>

  <!-- 静かな幾何学。テックの気配は最小限、絵の一部として -->
  <g stroke="{wire}" stroke-width="1.2" opacity="0.5" fill="none">
    <line x1="960" y1="120" x2="1120" y2="120"/>
    <circle cx="960" cy="120" r="3.5" fill="{wire}"/>
    <circle cx="1120" cy="120" r="3.5" fill="none"/>
  </g>

  <!-- 朱。渡されていない決裁の光 -->
  <circle cx="1000" cy="440" r="60" fill="#C0392F" opacity="0.10"/>
  <circle cx="1000" cy="440" r="26" fill="#C0392F" opacity="0.22" filter="url(#marble2)"/>
  <circle cx="1000" cy="440" r="15" fill="#C0392F" opacity="0.7"/>
  <circle cx="1000" cy="440" r="5" fill="#FBEDE9"/>

  <rect width="1200" height="630" filter="url(#grain)" opacity="0.6"/>

  <rect x="58" y="558" width="112" height="26" rx="4" fill="#F6F3EC" opacity="0.82"/>
  <text x="70" y="576" font-family="ui-monospace,monospace" font-size="12" letter-spacing="4" fill="#4A5162">{pillar}</text>
  <rect x="1030" y="558" width="112" height="26" rx="4" fill="#F6F3EC" opacity="0.82"/>
  <text x="1130" y="576" font-family="ui-monospace,monospace" font-size="12" letter-spacing="4" fill="#4A5162" text-anchor="end">R-{rno}</text>
</svg>
</body></html>
"""


def make(no: str, title: str, pillar: str, rinji: str = "", out_dir: str = "articles/og") -> str:
    """title は互換のため受け取るが、画像には焼き込まない（純粋にビジュアルのみ）。"""
    main, dark, wire = PILLAR_PALETTE.get(pillar, PILLAR_PALETTE["構築記録"])
    rno = (rinji or no).replace("R-", "").zfill(4)
    base = int(rno)
    html = TPL.format(
        main=main, dark=dark, wire=wire, pillar=pillar, rno=rno,
        seed1=11 + base % 50, seed2=33 + base % 40, seed3=18 + base % 30,
    )

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{no}.png")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html)
        page.screenshot(path=out_path)
        browser.close()

    return out_path


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print("使い方: python3 tools/og_image.py <記事番号> <pillar> [稟議番号]")
        sys.exit(1)
    no, pillar = sys.argv[1], sys.argv[2]
    rinji = sys.argv[3] if len(sys.argv) == 4 else ""
    p = make(no, "", pillar, rinji)
    print(f"  作成: {p}")
