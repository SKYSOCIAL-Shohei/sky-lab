##!/usr/bin/env python3
"""
記事の起案

Claude API を呼び、構築記録と考察の記事を作る。

「書かないもの」の制約を指示に組み込む。人が毎回気をつけるのではなく、
生成の時点で制約をかける。生成後は guard.py が別途検査する。

  使い方:  python3 tools/write.py
  必要な環境変数:  ANTHROPIC_API_KEY

失敗したときは、必ず理由をログに出す。黙って0本で終わらせない。
"""
import json, os, sys, re, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("SKYLAB_MODEL", "claude-sonnet-5")
WORK = "work"
MAX_TOKENS = int(os.environ.get("SKYLAB_MAX_TOKENS", "8000"))

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
- 本文が渡されている項目は、読んだうえで考察してよい。ただし必ず自分の言葉で書く。
  他社記事の要約や翻訳をそのまま貼り付けてはいけない。
- 直接引用は一文（40字程度）以内に留め、必ず「」で括り、出典をリンクで明記する。
  長い引用や、他社記事の構成をなぞっただけの要約にしない。
- 本文が渡されていない項目（見出しとリンクのみ）は、
  「〜と題した記事が公開されている」までにとどめ、内容を断定しない。
  詳細は原文を確認するよう促す。
- 英語の見出しを訳す場合も、逐語訳ではなく意味を自分の言葉で示す。
- 価値は「何が起きているか」の羅列や要約ではなく、
  「中小企業にとって何を意味しうるか」という自分の考察に置く。
"""

# 出力形式。3つのタグを必ず閉じさせる。
FORMAT = """次の形式で出力してください。前置きも、あとがきも書かないでください。

<title>記事タイトル</title>
<lead>1〜2文のリード</lead>
<body>本文のHTML</body>

<body> は必ず </body> で閉じてください。閉じられていないものは使えません。
文字数が足りなくなりそうなときは、本文を短くしてでも必ず閉じてください。"""


def call(system: str, user: str, max_tokens: int = MAX_TOKENS) -> str:
    """API を呼ぶ。失敗したら理由が分かる形で落とす。"""
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

    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"APIが{e.code}を返しました: {detail}") from None

    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text").strip()

    stop = data.get("stop_reason", "")
    used = data.get("usage", {}).get("output_tokens", "?")
    print(f"    返答 {len(text)}字／出力{used}トークン／終了理由={stop}")
    if stop == "max_tokens":
        print("    上限に達して途中で切れています。SKYLAB_MAX_TOKENS を上げてください。")

    return text


def parse_out(text: str, label: str) -> dict | None:
    """タイトル・リード・本文の3点を取り出す。取り出せない理由は必ず出す。"""

    def grab(tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S)
        if m:
            return m.group(1).strip()
        # 閉じタグが無い場合（途中で切れた場合）は、開始タグ以降を拾う
        m = re.search(rf"<{tag}>(.*)", text, re.S)
        return m.group(1).strip() if m else ""

    t, l, b = grab("title"), grab("lead"), grab("body")

    missing = [n for n, v in (("title", t), ("lead", l), ("body", b)) if not v]
    if missing:
        dump(label, text)
        print(f"    取り出せませんでした（欠けている: {', '.join(missing)}）")
        print(f"    返答の冒頭: {text[:160]!r}")
        return None

    if len(b) < 200:
        dump(label, text)
        print(f"    本文が短すぎます（{len(b)}字）。採用しません。")
        return None

    return {"title": t, "lead": l, "body": b}


def dump(label: str, text: str) -> None:
    """失敗した返答をそのまま残す。次に直すための材料。"""
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, f"raw-{label}.txt")
    open(path, "w", encoding="utf-8").write(text)
    print(f"    返答を {path} に保存しました。")


def write_kouchiku(nippou: dict) -> dict | None:
    """構築記録。前日の日報をもとに書く。"""
    entries = nippou.get("days", [{}])[0].get("entries", [])
    if len(entries) < 3:
        print(f"  日報の記録が{len(entries)}件しかないため、構築記録は作成しません。")
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
- 1,200〜2,000字程度
- 本文で使ってよいタグは h2, p, strong, ul, li のみ

{FORMAT}"""

    out = parse_out(call(system, user), "kouchiku")
    if out:
        out["pillar"] = "構築記録"
    return out


def write_kousatsu(collected: dict) -> dict | None:
    """収集と考察。拾えた情報がある日だけ書く。"""
    items = collected.get("items", [])
    if not items:
        print("  収集できた情報がないため、考察記事は作成しません。")
        return None

    with_body = sum(1 for i in items if i.get("body"))
    print(f"  材料 {len(items)}件（本文あり {with_body}件）")

    def fmt_item(i: dict) -> str:
        head = f"- [{i.get('category','')}／{i.get('source','')}] {i.get('title','')}\n  {i.get('link','')}"
        body = i.get("body")
        if body:
            return f"{head}\n  本文:\n{body}"
        return f"{head}\n  本文: （取得できませんでした。見出しのみで扱ってください）"

    src = "\n\n".join(fmt_item(i) for i in items)

    system = ("あなたはSKY SOCIAL LABの記録係です。国内の制度と世界のAI動向を"
              "毎日見て、中小企業にとって何を意味するかを考えます。"
              "推測と事実を混ぜてはいけません。"
              "本文が渡されている項目は読んだうえで考察し、渡されていない項目は"
              "見出し以上を語らないという区別を、項目ごとに厳密に守ってください。" + RULES)
    user = f"""以下は本日、公式のRSS配信から拾った項目です。項目ごとに、
記事ページの本文を取得できたものと、できなかったもの（見出しとリンクのみ）が
混ざっています。

{src}

これらを材料に、考察記事を1本書いてください。

要件:
- **中小企業の経営者にとって意味がありそうなものを2〜4件選ぶ。**
  国内の制度の話と、世界のAI・技術動向の両方から選べるとよい
- 本文がある項目は、読んだ内容を自分の言葉で考察してよい。
  本文がない項目は、「〜と題した発表があった」「〜という記事が出ている」
  という書き方にとどめ、内容を断定しない
- 各項目には必ず出典リンクを <a href="URL">出典元の名称</a> の形で入れる
- 見出しの羅列にしない。**「これが何を意味しうるか」の考察を主役にする**
- 海外の動きは、日本の中小企業にいつ・どう効いてくるかという時間差の視点で書く
- 関係が薄いと判断した項目は取り上げない。無理に増やさない
- 外れる可能性のある見立てには「現時点ではそう見える」と明示する
- 1,200〜2,000字程度
- 本文で使ってよいタグは h2, p, strong, ul, li, a のみ

{FORMAT}"""

    out = parse_out(call(system, user), "kousatsu")
    if out:
        out["pillar"] = "収集と考察"
    return out


def main() -> int:
    print(f"記事の起案　{datetime.now(JST):%Y-%m-%d %H:%M}"
          f"　model={MODEL}　上限={MAX_TOKENS}トークン\n")

    nippou = json.load(open("ledger/nippou.json", encoding="utf-8"))
    collected = {}
    p = os.path.join(WORK, "collected.json")
    if os.path.exists(p):
        collected = json.load(open(p, encoding="utf-8"))
    else:
        print(f"  {p} がありません。収集が動いていない可能性があります。\n")

    drafts, failed = [], []
    for name, fn, arg in (("構築記録", write_kouchiku, nippou),
                          ("収集と考察", write_kousatsu, collected)):
        print(f"  {name}")
        try:
            d = fn(arg)
        except Exception as e:
            print(f"    作成できませんでした: {e}")
            failed.append(name)
            d = None
        if d:
            print(f"    「{d['title']}」　本文{len(d['body'])}字")
            drafts.append(d)
        print()

    os.makedirs(WORK, exist_ok=True)
    json.dump({"drafts": drafts},
              open(os.path.join(WORK, "drafts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"  {len(drafts)}本を起案しました。")
    if failed:
        print(f"  失敗: {', '.join(failed)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
