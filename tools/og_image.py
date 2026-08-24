#!/usr/bin/env python3
"""
記事の見出し画像（The Withheld Seal）

写真ではなく、抽象アートで記事のテーマを象徴的に表す。
「境界線」と「まだ押されていない印（決裁の輪）」で、
AIが持たない決裁の権限を表現する。タイトルの文字は入れない
（タイトルは記事ページ側で別途テキストとして表示される）。

pillar（構築記録／収集と考察）によって色調だけを切り替える。
すべての記事で同じ構図を使うのは手抜きではなく意図で、
「同じ様式の記録が積み重なっていく」こと自体が主題である。

Playwrightで実際に描画してスクリーンショットし、1200x630のPNGにする。

  使い方:  python3 tools/og_image.py 012 構築記録
  出力:    articles/og/012.png
"""
import os, sys
from playwright.sync_api import sync_playwright

PILLAR_COLOR = {
    "構築記録": "#2C4A6E",
    "収集と考察": "#6E5330",
}

TPL = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  *{{margin:0;padding:0}}
  html,body{{width:1200px;height:630px;overflow:hidden;background:#FBFAF7}}
</style></head>
<body>
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="ringLeft"><rect x="0" y="0" width="430" height="630"/></clipPath>
    <clipPath id="ringRight"><rect x="430" y="0" width="770" height="630"/></clipPath>
    <pattern id="hair" width="18" height="18" patternTransform="rotate(-25)" patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="18" stroke="#FBFAF7" stroke-width="1" opacity="0.09"/>
    </pattern>
  </defs>

  <rect x="0" y="0" width="1200" height="630" fill="#FBFAF7"/>

  <!-- 種別の色の領域（システム側） -->
  <rect x="0" y="0" width="430" height="630" fill="{color}"/>
  <rect x="0" y="0" width="430" height="630" fill="url(#hair)"/>

  <!-- 境界線 -->
  <line x1="430" y1="0" x2="430" y2="630" stroke="#1A1D24" stroke-width="1" opacity="0.12"/>

  <!-- 印環（決裁の輪）。中心を境界線上、やや下寄りに置く -->
  <circle cx="430" cy="356" r="136" fill="none" stroke="#EDE9E0" stroke-width="2" clip-path="url(#ringLeft)" opacity="0.92"/>
  <circle cx="430" cy="356" r="136" fill="none" stroke="{color}" stroke-width="2" clip-path="url(#ringRight)" opacity="0.92"/>
  <circle cx="430" cy="356" r="118" fill="none" stroke="#EDE9E0" stroke-width="1" clip-path="url(#ringLeft)" opacity="0.45"/>
  <circle cx="430" cy="356" r="118" fill="none" stroke="{color}" stroke-width="1" clip-path="url(#ringRight)" opacity="0.45"/>

  <!-- 朱。まだ押されていない、という含意で輪の一部の弧だけに -->
  <path d="M 452 221 A 136 136 0 0 1 508 249" fill="none" stroke="#C0392F" stroke-width="2" stroke-linecap="round" opacity="0.8"/>

  <!-- 登録記号のような、控えめな参照テキスト -->
  <text x="1130" y="580" font-family="ui-monospace,monospace" font-size="13" letter-spacing="3" fill="#828A9A" text-anchor="end">SKY SOCIAL LAB · R-{rno}</text>
  <text x="70" y="580" font-family="ui-monospace,monospace" font-size="13" letter-spacing="3" fill="#EDE9E0" opacity="0.55">{pillar}</text>
</svg>
</body></html>
"""


def make(no: str, title: str, pillar: str, rinji: str = "", out_dir: str = "articles/og") -> str:
    """title は互換のため受け取るが、画像には焼き込まない（純粋にビジュアルのみ）。"""
    color = PILLAR_COLOR.get(pillar, PILLAR_COLOR["構築記録"])
    rno = (rinji or no).replace("R-", "").zfill(4)
    html = TPL.format(color=color, pillar=pillar, rno=rno)

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
