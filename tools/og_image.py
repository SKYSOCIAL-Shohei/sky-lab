#!/usr/bin/env python3
"""
OGP画像の生成

記事の見出し帯（hband）と同じ意匠で、SNSシェア用のカード画像を作る。
写真は使わず、抽象グラフィック（グラデーション＋斜線の質感）とタイトルのみ。
Playwrightでブラウザに実際に描画させ、1200x630のPNGとして保存する。

  使い方:  python3 tools/og_image.py 012 "記事タイトル" 構築記録
  出力:    articles/og/012.png
"""
import sys, os
from playwright.sync_api import sync_playwright

PILLAR_COLOR = {
    "構築記録": ("#2C4A6E", "#203a56"),
    "収集と考察": ("#6E5330", "#4d3a22"),
}

TPL = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  *{{box-sizing:border-box}}
  html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
  body{{
    font-family:"Hiragino Kaku Gothic ProN","Hiragino Mincho ProN",sans-serif;
    background:linear-gradient(155deg, {c1} 0%, {c2} 100%);
    position:relative;padding:64px 68px;color:#fff;
  }}
  body::after{{
    content:"";position:absolute;inset:0;opacity:.5;
    background:repeating-linear-gradient(115deg, rgba(255,255,255,.08) 0px, rgba(255,255,255,.08) 1px, transparent 1px, transparent 22px);
  }}
  .logo{{position:relative;font-size:20px;letter-spacing:.16em;opacity:.85}}
  .pillar{{position:relative;display:inline-block;margin-top:210px;font-size:17px;font-weight:600;
    padding:7px 18px;border-radius:100px;background:rgba(255,255,255,.24);letter-spacing:.04em}}
  h1{{position:relative;font-family:"Hiragino Mincho ProN","Yu Mincho",serif;font-weight:400;
    font-size:46px;line-height:1.5;letter-spacing:.02em;margin:22px 0 0;max-width:1000px}}
  .no{{position:relative;margin-top:24px;font-size:16px;opacity:.7;font-family:ui-monospace,monospace;letter-spacing:.06em}}
</style></head>
<body>
  <div class="logo">SKY SOCIAL LAB</div>
  <div class="pillar">{pillar}</div>
  <h1>{title}</h1>
  <div class="no">No.{no}</div>
</body></html>
"""


def make(no: str, title: str, pillar: str, out_dir: str = "articles/og") -> str:
    c1, c2 = PILLAR_COLOR.get(pillar, PILLAR_COLOR["構築記録"])
    html = TPL.format(c1=c1, c2=c2, pillar=pillar, title=title, no=no)

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
    if len(sys.argv) != 4:
        print("使い方: python3 tools/og_image.py <記事番号> <タイトル> <pillar>")
        sys.exit(1)
    p = make(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"  作成: {p}")
