#!/usr/bin/env python3
"""
記事の見出し画像

写真ではなく、記事のテーマを回路図（システムのパイプライン）として
象徴的に表す。起案から公開までの一本の配線の途中に「HUMAN」ゲートが
あり、そこがまだ閉じていない（スイッチが開いたまま）ことで、
承認がまだAIの手を離れて人間に委ねられている状態を表現する。
タイトルの文字は入れない（タイトルは記事ページ側で別途表示される）。

pillar（構築記録／収集と考察）によって色調だけを切り替える。
すべての記事で同じ回路図を使うのは意図的で、記録が同じ様式で
淡々と積み重なっていくこと自体を表している。

Playwrightで実際に描画してスクリーンショットし、1200x630のPNGにする。

  使い方:  python3 tools/og_image.py 012 構築記録 R-0015
  出力:    articles/og/012.png
"""
import os, sys
from playwright.sync_api import sync_playwright

# (背景, グリッド線, 配線, ラベル文字) の4色セット
PILLAR_PALETTE = {
    "構築記録":   ("#12213A", "#3A5A82", "#6E8CB8", "#8CA3C4"),
    "収集と考察": ("#2B2114", "#7A6242", "#B89A6E", "#C4B08C"),
}

TPL = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  *{{margin:0;padding:0}}
  html,body{{width:1200px;height:630px;overflow:hidden;background:{bg}}}
</style></head>
<body>
<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="{grid}" stroke-width="1" opacity="0.35"/>
    </pattern>
    <radialGradient id="glow" cx="50%" cy="50%" r="60%">
      <stop offset="0%" stop-color="{wire}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{bg}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="1200" height="630" fill="{bg}"/>
  <rect width="1200" height="630" fill="url(#grid)"/>
  <circle cx="600" cy="315" r="360" fill="url(#glow)"/>

  <!-- 回路トレース：起案 → 承認(未通過) → 公開、という一本のパイプライン -->
  <g fill="none" stroke="{wire}" stroke-width="2" opacity="0.55">
    <path d="M 120 315 H 420"/>
    <path d="M 420 315 V 220 H 560"/>
    <path d="M 420 315 V 410 H 560"/>
    <path d="M 780 220 H 920 V 315 H 1080"/>
    <path d="M 780 410 H 920 V 315"/>
  </g>

  <!-- ノード：起案（点灯） -->
  <circle cx="120" cy="315" r="9" fill="{wire}"/>
  <circle cx="120" cy="315" r="16" fill="none" stroke="{wire}" stroke-width="1.5" opacity="0.5"/>
  <circle cx="420" cy="315" r="6" fill="{wire}"/>

  <!-- ゲート：承認（開いた回路＝まだ閉じていない＝未承認）。朱で強調 -->
  <g>
    <rect x="560" y="196" width="220" height="48" rx="8" fill="{bg}" stroke="#C0392F" stroke-width="2"/>
    <line x1="560" y1="220" x2="600" y2="220" stroke="#C0392F" stroke-width="2"/>
    <line x1="740" y1="220" x2="780" y2="220" stroke="#C0392F" stroke-width="2"/>
    <text x="670" y="226" font-family="ui-monospace,monospace" font-size="15" letter-spacing="2" fill="#C0392F" text-anchor="middle">HUMAN</text>
    <circle cx="620" cy="220" r="4" fill="#C0392F"/>
    <circle cx="720" cy="220" r="4" fill="#C0392F"/>
    <line x1="620" y1="220" x2="712" y2="205" stroke="#C0392F" stroke-width="2" stroke-linecap="round"/>
  </g>

  <!-- 下側の回路（同じく承認待ち） -->
  <g>
    <rect x="560" y="386" width="220" height="48" rx="8" fill="{bg}" stroke="#C0392F" stroke-width="2" opacity="0.55"/>
    <line x1="560" y1="410" x2="600" y2="410" stroke="#C0392F" stroke-width="2" opacity="0.55"/>
    <line x1="740" y1="410" x2="780" y2="410" stroke="#C0392F" stroke-width="2" opacity="0.55"/>
  </g>

  <!-- 終端ノード（公開）。回路が閉じていないので消灯 -->
  <circle cx="1080" cy="315" r="9" fill="none" stroke="{wire}" stroke-width="2"/>

  <!-- HUDふうの計測線・座標ラベル -->
  <g font-family="ui-monospace,monospace" fill="{label}" opacity="0.6">
    <text x="70" y="80" font-size="13" letter-spacing="3">PIPELINE // DRAFT -&gt; REVIEW -&gt; PUBLISH</text>
    <text x="70" y="100" font-size="13" letter-spacing="3" opacity="0.7">STATUS: AWAITING HUMAN APPROVAL</text>
  </g>

  <text x="1130" y="580" font-family="ui-monospace,monospace" font-size="13" letter-spacing="3" fill="{label}" text-anchor="end">SKY SOCIAL LAB · R-{rno}</text>
  <text x="70" y="580" font-family="ui-monospace,monospace" font-size="13" letter-spacing="3" fill="{label}" opacity="0.8">{pillar}</text>

  <!-- 外枠。基板のシルクスクリーンふうの角マーク -->
  <g stroke="{grid}" stroke-width="1.5" opacity="0.5">
    <path d="M 40 40 H 70 M 40 40 V 70"/>
    <path d="M 1160 40 H 1130 M 1160 40 V 70"/>
    <path d="M 40 590 H 70 M 40 590 V 560"/>
    <path d="M 1160 590 H 1130 M 1160 590 V 560"/>
  </g>
</svg>
</body></html>
"""


def make(no: str, title: str, pillar: str, rinji: str = "", out_dir: str = "articles/og") -> str:
    """title は互換のため受け取るが、画像には焼き込まない（純粋にビジュアルのみ）。"""
    bg, grid, wire, label = PILLAR_PALETTE.get(pillar, PILLAR_PALETTE["構築記録"])
    rno = (rinji or no).replace("R-", "").zfill(4)
    html = TPL.format(bg=bg, grid=grid, wire=wire, label=label, pillar=pillar, rno=rno)

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
