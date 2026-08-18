#!/usr/bin/env python3
"""
記事の起案

Claude API を呼び、構築記録と考察の記事を作る。

「書かないもの」の制約を指示に組み込む。人が毎回気をつけるのではなく、
生成の時点で制約をかける。生成後は guard.py が別途検査する。

  使い方:  python3 tools/write.py
  必要な環境変数:  ANTHROPIC_API_KEY
"""
import json, os, sys, re, html, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("SKYLAB_MODEL", "claude-sonnet-5")
WORK = "work"

# ── 書かないもの。運営方針と一致させる ──
RULES = """
【絶対に書いてはいけないこと】
- ホスト名、IPアドレス、DNSレコードの値、メール認証の設定
- APIキー、パスワード、トークン、鍵に類するもの
- 利用しているサービスやホスティングの構成、事業者名
- システムの不具合、エラー、障害の内容
- 攻撃の手がかりになり得る一切の技術的詳細
- 顧客・取引先を特定できる情報

判断の過程は書いてよいが、設定値と障害内容は書かない。
迷ったら書かない。

【書き方】
- 事実と考察を明確に分ける
- 断定しない。報道や発表を根拠にする場合は「発表されている」「示されている」までにとどめる
- 誇張しない。数字を作らない。確認できないことは書かない
- 見出しは <h2>、段落は <p>、強調は <strong> を使う
- 出典は必ずリンクで示す

【他者の記事を扱うときの決まり】
- 受け取っているのは見出しとリンクだけで、本文は読んでいない。
  したがって記事の中身を要約してはいけない。断定してもいけない。
- 「〜と題した記事が公開されている」までにとどめ、
  内容の判断は読者に委ねる。詳細は原文を確認するよう促す。
- 見出しの引用は最小限にする。長い引用や、複数の見出しを並べただけの
  記事にしてはいけない。
- 英語の見出しを訳す場合も、逐語訳ではなく意味を自分の言葉で示す。
- 価値は「何が起きているか」の羅列ではなく、
  「中小企業にとって何を意味しうるか」という自分の考察に置く。
"""


def call(system: str, user: str, max_tokens: int = 3000) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")

    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")

    req = urllib.request.Request(API, data=body, headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())

    return "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text").strip()


def parse_out(text: str) -> dict | None:
    """タイトル・リード・本文の3点を取り出す。"""
    def grab(tag):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S)
        return m.group(1).strip() if m else ""
    t, l, b = grab("title"), grab("lead"), grab("body")
    if not (t and l and b):
        return None
    return {"title": t, "lead": l, "body": b}


def write_kouchiku(nippou: dict) -> dict | None:
    """構築記録。前日の日報をもとに書く。"""
    entries = nippou.get("days", [{}])[0].get("entries", [])
    if len(entries) < 3:
        print("  日報の記録が少ないため、構築記録は作成しません。")
        return None

    log = "\n".join(f"- {e.get('who','')}: {e.get('what','')}" for e in entries)

    system = ("あなたはSKY SOCIAL LABの記録係です。AIだけで事業を作る過程を、"
              "失敗も含めて誠実に記録します。読者は中小企業の経営者です。"
              + RULES)
    user = f"""以下は本日の作業記録です。これをもとに、構築記録の記事を1本書いてください。

{log}

要件:
- 何を判断し、なぜそう決めたかを中心に書く
- うまくいかなかったことがあれば、そのまま書く
- 中小企業の読者が自分の会社に当てはめて考えられる示唆で締める
- 1,500〜2,500字程度

次の形式で出力してください。前置きは書かないでください。

<title>記事タイトル</title>
<lead>1〜2文のリード</lead>
<body>本文のHTML（h2, p, strong, ul, li のみ使用）</body>"""

    out = parse_out(call(system, user))
    if out:
        out["pillar"] = "構築記録"
    return out


def write_kousatsu(collected: dict) -> dict | None:
    """収集と考察。拾えた情報がある日だけ書く。"""
    items = collected.get("items", [])
    if not items:
        print("  収集できた情報がないため、考察記事は作成しません。")
        return None

    src = "\n".join(
        f"- [{i.get('category','')}／{i.get('source','')}] {i.get('title','')}\n"
        f"  {i.get('link','')}"
        for i in items)

    system = ("あなたはSKY SOCIAL LABの記録係です。国内の制度と世界のAI動向を"
              "毎日見て、中小企業にとって何を意味するかを考えます。"
              "推測と事実を混ぜてはいけません。"
              "見出ししか読んでいないことを、常に念頭に置いてください。" + RULES)
    user = f"""以下は本日、公式のRSS配信から拾った見出しです。
本文は取得していません。見出しとリンクだけです。

{src}

これらを材料に、考察記事を1本書いてください。

要件:
- **中小企業の経営者にとって意味がありそうなものを2〜4件選ぶ。**
  国内の制度の話と、世界のAI・技術動向の両方から選べるとよい
- **本文を読んでいないことを前提にする。**内容を断定せず、
  「〜と題した発表があった」「〜という記事が出ている」という書き方にする
- 各項目には必ず出典リンクを <a href="URL">出典元の名称</a> の形で入れる
- 見出しの羅列にしない。**「これが何を意味しうるか」の考察を主役にする**
- 海外の動きは、日本の中小企業にいつ・どう効いてくるかという時間差の視点で書く
- 関係が薄いと判断した項目は取り上げない。無理に増やさない
- 外れる可能性のある見立てには「現時点ではそう見える」と明示する
- 1,500〜2,500字程度

次の形式で出力してください。前置きは書かないでください。

<title>記事タイトル</title>
<lead>1〜2文のリード</lead>
<body>本文のHTML（h2, p, strong, ul, li, a のみ使用）</body>"""

    out = parse_out(call(system, user))
    if out:
        out["pillar"] = "収集と考察"
    return out


def main() -> int:
    print(f"記事の起案　{datetime.now(JST):%Y-%m-%d %H:%M}　model={MODEL}\n")

    nippou = json.load(open("ledger/nippou.json", encoding="utf-8"))
    collected = {}
    p = os.path.join(WORK, "collected.json")
    if os.path.exists(p):
        collected = json.load(open(p, encoding="utf-8"))

    drafts = []
    for name, fn, arg in (("構築記録", write_kouchiku, nippou),
                          ("収集と考察", write_kousatsu, collected)):
        print(f"  {name}")
        try:
            d = fn(arg)
        except Exception as e:
            print(f"    作成できませんでした: {type(e).__name__}")
            d = None
        if d:
            print(f"    「{d['title']}」")
            drafts.append(d)

    os.makedirs(WORK, exist_ok=True)
    json.dump({"drafts": drafts},
              open(os.path.join(WORK, "drafts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"\n  {len(drafts)}本を起案しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
