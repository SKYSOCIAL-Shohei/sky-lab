#!/usr/bin/env python3
"""
記事の見出し写真（Pexels）

記事のタイトル・リードをAIに読ませ、内容の抽象的なテーマを表す
英語の検索語を考えさせたうえで、Pexelsの無料APIで写真を探す。
実在の写真なので、記事の具体的な内容そのものを写しているわけでは
ない（そのような写真は存在しない）。あくまで雰囲気・象徴としての
写真であることを前提にしている。

Pexelsの利用規約上、クレジット表記は必須ではないが、礼儀として
撮影者名とPexelsへのリンクを小さく添える。

  使い方:  python3 tools/photo_image.py 012 "記事タイトル" "リード文" 構築記録
  出力:    articles/og/012.jpg
"""
import hashlib, json, os, sys, urllib.request, urllib.error, urllib.parse

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"


def file_hash(path: str) -> str:
    """画像URLに付けるキャッシュ対策用の短いハッシュ値。"""
    return hashlib.md5(open(path, "rb").read()).hexdigest()[:8]

MODEL = os.environ.get("SKYLAB_MODEL", "claude-sonnet-5")
PEXELS_API = "https://api.pexels.com/v1/search"
# PexelsはCloudflareの防御下にあり、Pythonの既定User-Agentだと
# エラーコード1010（WAFによる遮断）で弾かれる。明示的に名乗る。
UA = "sky-lab/1.0 (+https://lab.sky-social.com)"

# AIでの検索語提案が失敗した場合の、pillarごとの最低限のフォールバック
FALLBACK_QUERY = {
    "構築記録": "architecture minimal line",
    "収集と考察": "newspaper archive texture",
}


def suggest_query(title: str, lead: str, pillar: str) -> str:
    """記事の内容から、Pexels検索に使う英語キーワードをAIに考えさせる。"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return FALLBACK_QUERY.get(pillar, "abstract minimal")

    system = (
        "あなたはストックフォトのアートディレクターです。"
        "与えられた記事の見出しとリード文から、記事の抽象的なテーマや雰囲気を"
        "象徴する、英語の検索キーワードを2〜4語だけ考えてください。"
        "『男性がノートパソコンを使っている』のような、内容と無関係などの記事にも"
        "使い回せる汎用的なビジネス写真は避けてください。"
        "代わりに、印章・扉・境界線・回路・古い紙・光と影、といった"
        "抽象的・象徴的で、かつ実在する写真として存在しそうなモチーフを選んでください。"
        "出力はキーワードのみ。説明や記号、引用符は不要です。"
    )
    user = f"見出し: {title}\nリード文: {lead}\n種別: {pillar}"

    body = json.dumps({
        "model": MODEL, "max_tokens": 60,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_API, data=body, headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text").strip()
        text = text.strip().strip('"').strip("'")
        if text:
            print(f"    検索語（AI提案）: {text}")
            return text
    except Exception as e:
        print(f"    検索語の提案に失敗、既定語を使う: {e}")
    return FALLBACK_QUERY.get(pillar, "abstract minimal")


def search_pexels(query: str, api_key: str, pick: int = 0):
    """Pexelsを検索し、1枚選んで (画像URL, 撮影者名, 撮影者ページURL) を返す。
    pick は検索結果の何枚目を選ぶか。同じ検索語でも記事ごとに違う写真に
    なるよう、呼び出し側で記事番号から決めた値を渡す。"""
    url = f"{PEXELS_API}?query={urllib.parse.quote(query)}&per_page=50&orientation=landscape"
    req = urllib.request.Request(url, headers={"Authorization": api_key, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    photos = data.get("photos", [])
    if not photos:
        return None
    p = photos[pick % len(photos)]
    return p["src"]["landscape"], p.get("photographer", "Pexels"), p.get("photographer_url", "https://www.pexels.com")


def make(no: str, title: str, lead: str, pillar: str, rinji: str = "", out_dir: str = "articles/og"):
    """写真をダウンロードして保存する。(ファイルパス, 撮影者名, 撮影者URL) を返す。
    Pexelsで見つからない場合は None を返す（呼び出し側でフォールバックすること）。"""
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        raise RuntimeError("PEXELS_API_KEY が設定されていません")

    query = suggest_query(title, lead, pillar)
    # 記事番号・稟議番号・検索語からハッシュを作り、それで検索結果の
    # 何枚目を選ぶかを決める。単純な余り演算だと周期的に衝突するため、
    # ハッシュ値をそのまま渡し、実際の検索結果数で割った余りを
    # search_pexels 側で取る（結果数に応じて自然に分散する）。
    seed_src = f"{no}-{rinji or no}-{query}".encode()
    pick = int(hashlib.md5(seed_src).hexdigest(), 16)

    hit = None
    for q in (query, FALLBACK_QUERY.get(pillar, "abstract minimal")):
        hit = search_pexels(q, api_key, pick)
        if hit:
            break
    if not hit:
        return None

    img_url, photographer, photographer_url = hit
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{no}.jpg")
    img_req = urllib.request.Request(img_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(img_req, timeout=60) as r:
        open(out_path, "wb").write(r.read())

    print(f"    保存: {out_path}（撮影 {photographer} / Pexels）")
    return out_path, photographer, photographer_url


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("使い方: python3 tools/photo_image.py <記事番号> <タイトル> <リード文> <pillar>")
        sys.exit(1)
    no, title, lead, pillar = sys.argv[1:5]
    result = make(no, title, lead, pillar)
    if result:
        path, photographer, url = result
        print(f"  作成: {path}（{photographer}）")
    else:
        print("  写真が見つかりませんでした。")
        sys.exit(1)
