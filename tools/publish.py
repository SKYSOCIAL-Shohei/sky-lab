#!/usr/bin/env python3
"""
記事ページの生成と台帳への記入

work/drafts.json を読み、記事HTMLを作り、
記事台帳・稟議・日報・トップページを更新する。

稟議は必ず未承認（pending）で起票する。
承認欄はこの処理では触らない。承認は人間の操作でのみ記録される。
"""
import json, os, sys, re, html
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
WORK = "work/drafts.json"

TPL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — SKY SOCIAL LAB</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="../style.css">
</head>
<body>

<header><div class="hd">
  <a href="../" class="logo">SKY SOCIAL LAB</a>
  <nav class="nav"><a href="../">記録</a><a href="../rinji.html">稟議</a><a href="../about.html">このサイトについて</a></nav>
</div></header>

<div class="wrap">
<article>
  <div class="a-head">
    <div class="erow">
      <span class="eno">No.{no}</span>
      <span class="pillar">{pillar}</span>
    </div>
    <h1>{title}</h1>
    <p class="lead">{lead}</p>
  </div>

  <div class="a-body">
{body}
  </div>

  <div class="stampbox">
    <svg class="stamp" viewBox="0 0 100 100" role="img" aria-label="承認済">
      <circle cx="50" cy="50" r="46" fill="none" stroke="#C0392F" stroke-width="3.5"/>
      <line x1="10" y1="50" x2="90" y2="50" stroke="#C0392F" stroke-width="1.6"/>
      <text x="50" y="34" font-family="'Hiragino Mincho ProN','Yu Mincho',serif" font-size="27" fill="#C0392F" text-anchor="middle">承認</text>
      <text x="50" y="72" font-family="'Hiragino Mincho ProN','Yu Mincho',serif" font-size="18" fill="#C0392F" text-anchor="middle">池田</text>
    </svg>
    <div class="stampinfo">
      稟議番号　<em>{rinji}</em><br>
      起案　<em>SKY SOCIAL LAB / Claude</em><br>
      承認　<em>池田 昌平</em><br>
      公開　<em>{date}</em>
    </div>
  </div>

  <p class="disclosure">この記事はAIが起案し、人間が内容を確認・承認したうえで公開しています。事実関係の誤りが判明した場合は、修正内容を明記したうえで訂正します。</p>
</article>
</div>

<footer><div class="ft">
  <span>SKY SOCIAL LAB</span>
  <span><a href="https://www.sky-social.com">SKY SOCIAL株式会社</a></span>
</div></footer>

</body>
</html>
"""

ENTRY = """  <a class="entry" href="articles/{no}.html">
    <div class="erow">
      <span class="eno">No.{no}</span>
      <span class="pillar">{pillar}</span>
    </div>
    <div class="etitle">{title}</div>
    <div class="elead">{lead}</div>
    <div class="edate">{date} ／ 稟議 {rinji}</div>
  </a>
"""


def load(p, default):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def save(p, obj):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def next_no(articles, width=3):
    nums = [int(a["no"]) for a in articles if str(a.get("no", "")).isdigit()]
    return f"{(max(nums) + 1) if nums else 1:0{width}d}"


def next_rinji(rinji):
    nums = [int(m.group(1)) for x in rinji
            if (m := re.match(r"R-(\d+)$", x.get("no", "")))]
    return f"R-{(max(nums) + 1) if nums else 1:04d}"


def main() -> int:
    drafts = load(WORK, {}).get("drafts", [])
    if not drafts:
        print("起案された記事がありません。何もしません。")
        return 0

    today = datetime.now(JST).strftime("%Y-%m-%d")
    arts = load("ledger/articles.json", {"articles": []})
    rin = load("ledger/rinji.json", {"rinji": []})
    nip = load("ledger/nippou.json", {"days": []})

    made = []
    for d in drafts:
        no = next_no(arts["articles"])
        rno = next_rinji(rin["rinji"])
        title = d["title"]
        page = TPL.format(
            title=html.escape(title), desc=html.escape(d["lead"]),
            no=no, pillar=html.escape(d["pillar"]),
            lead=html.escape(d["lead"]), body=d["body"],
            rinji=rno, date=today)

        os.makedirs("articles", exist_ok=True)
        open(f"articles/{no}.html", "w", encoding="utf-8").write(page)

        arts["articles"].insert(0, {
            "no": no, "file": f"articles/{no}.html", "pillar": d["pillar"],
            "title": title, "lead": d["lead"],
            "drafted_by": "Claude", "drafted_at": today,
            "rinji": rno, "published_at": None, "status": "pending"})

        rin["rinji"].append({
            "no": rno, "subject": f"記事 No.{no} を公開する",
            "detail": f"「{title}」を公開します。",
            "proposed_by": "Claude", "proposed_at": today,
            "status": "pending", "approved_by": None, "approved_at": None,
            "article": f"articles/{no}.html"})

        made.append({"no": no, "rinji": rno, "title": title,
                     "pillar": d["pillar"], "lead": d["lead"]})
        print(f"  No.{no}  {rno}  {title}")

    # トップページの一覧を差し替える
    idx = open("index.html", encoding="utf-8").read()
    new = "".join(ENTRY.format(no=m["no"], pillar=html.escape(m["pillar"]),
                               title=html.escape(m["title"]),
                               lead=html.escape(m["lead"]),
                               date=today, rinji=m["rinji"])
                  for m in reversed(made))
    idx = idx.replace('  <div class="sect-label">記録</div>\n',
                      '  <div class="sect-label">記録</div>\n\n' + new, 1)
    idx = re.sub(r"記録 \d+件", f"記録 {len(arts['articles'])}件", idx)
    open("index.html", "w", encoding="utf-8").write(idx)

    # 日報
    day = next((d for d in nip["days"] if d["date"] == today), None)
    if day is None:
        day = {"date": today, "entries": []}
        nip["days"].insert(0, day)
    for m in made:
        day["entries"].append(
            {"time": "—", "who": "Claude",
             "what": f"記事 No.{m['no']} を起案し、稟議 {m['rinji']} を起票"})

    save("ledger/articles.json", arts)
    save("ledger/rinji.json", rin)
    save("ledger/nippou.json", nip)

    print(f"\n  {len(made)}本を作成しました。稟議はすべて未承認です。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
