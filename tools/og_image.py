#!/usr/bin/env python3
"""
記事の見出し画像

写真ではなく、絵画的な抽象アートで記事のテーマを表す。
密集した粒子の群れ（システム側の処理）が、左から右へ向かうにつれ
散り、薄れていき、その先に小さな朱の光がひとつだけ灯っている
（まだ渡されていない、決裁という一点）。図解ではなく、雰囲気で
「AIの領域から、人間だけに委ねられた一点がある」ことを表す。

タイトルの文字は入れない。pillar（構築記録／収集と考察）で
色調（藍／焦茶）だけを切り替える。粒子の配置は固定シードの疑似乱数
なので、同じ記事番号なら常に同じ絵になる。

Playwrightで実際に描画してスクリーンショットし、1200x630のPNGにする。

  使い方:  python3 tools/og_image.py 012 構築記録 R-0015
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
    <filter id="soft" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="18"/>
    </filter>
    <filter id="soft2" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="6"/>
    </filter>
    <radialGradient id="core" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="wash" x1="0" y1="0" x2="1" y2="0.3">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.55"/>
      <stop offset="55%" stop-color="{color}" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect width="1200" height="630" fill="#FBFAF7"/>
  <rect width="1200" height="630" fill="url(#wash)"/>
  <ellipse cx="120" cy="300" rx="420" ry="360" fill="url(#core)" filter="url(#soft)"/>

  <!-- 粒子の群れ。密から疎へ、藍/焦茶から透明へ流れる -->
  <g id="particles"></g>

  <!-- 朱。まだ渡されていない、決裁という一点 -->
  <circle cx="760" cy="260" r="46" fill="#C0392F" opacity="0.16" filter="url(#soft)"/>
  <circle cx="760" cy="260" r="14" fill="#C0392F" opacity="0.55" filter="url(#soft2)"/>
  <circle cx="760" cy="260" r="4" fill="#C0392F" opacity="0.9"/>

  <!-- 筆で引いたような、水平を少し外れた一本の線 -->
  <path d="M 40 460 C 300 430, 650 500, 1160 380" fill="none" stroke="#1A1D24" stroke-width="1.2" opacity="0.18"/>

  <text x="70" y="580" font-family="ui-monospace,monospace" font-size="12" letter-spacing="4" fill="#828A9A" opacity="0.6">{pillar}</text>
  <text x="1130" y="580" font-family="ui-monospace,monospace" font-size="12" letter-spacing="4" fill="#828A9A" text-anchor="end" opacity="0.6">R-{rno}</text>

  <script>
    const ns = "http://www.w3.org/2000/svg";
    const g = document.getElementById("particles");
    let seed = {seed};
    function rnd() {{ seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }}
    for (let i = 0; i < 260; i++) {{
      const t = rnd();
      const x = 60 + t * t * 1050 + (rnd() - 0.5) * 60;
      const spread = 60 + t * 320;
      const y = 315 + (rnd() - 0.5) * spread;
      const r = (1 - t) * 5 + 0.6 + rnd() * 1.5;
      const op = Math.max(0.04, (1 - t) * 0.55 - rnd() * 0.15);
      const c = document.createElementNS(ns, "circle");
      c.setAttribute("cx", x.toFixed(1));
      c.setAttribute("cy", y.toFixed(1));
      c.setAttribute("r", r.toFixed(2));
      c.setAttribute("fill", "{color}");
      c.setAttribute("opacity", op.toFixed(3));
      g.appendChild(c);
    }}
  </script>
</svg>
</body></html>
"""


def make(no: str, title: str, pillar: str, rinji: str = "", out_dir: str = "articles/og") -> str:
    """title は互換のため受け取るが、画像には焼き込まない（純粋にビジュアルのみ）。"""
    color = PILLAR_COLOR.get(pillar, PILLAR_COLOR["構築記録"])
    rno = (rinji or no).replace("R-", "").zfill(4)
    seed = int(rno) * 97 + 42  # 記事ごとに粒子の配置を変える固定シード
    html = TPL.format(color=color, pillar=pillar, rno=rno, seed=seed)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{no}.png")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html)
        page.wait_for_timeout(150)
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
