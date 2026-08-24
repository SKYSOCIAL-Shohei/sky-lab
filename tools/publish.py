#!/usr/bin/env python3
"""
記事ページの生成と台帳への記入

work/drafts.json を読み、記事HTMLを作り、
記事台帳・稟議・日報を更新し、トップページを組み直す。

トップページは構築記録を主役に置く。
構築記録はあとから通読される資産、収集と考察はその日のダイジェスト。
寿命が違うものを同じ大きさで並べない。

稟議は必ず未承認（pending）で起票する。
記事ページの決裁欄はHTMLに書き込まない。表示時に台帳から読む。

  python3 tools/publish.py            起案されたものを記事にする
  python3 tools/publish.py --index    トップページだけ組み直す
"""
import json, os, sys, re, html
from datetime import datetime, timezone, timedelta
import og_image

JST = timezone(timedelta(hours=9))
WORK = "work/drafts.json"
COLLECTED = "work/collected.json"
SINCE = "2026-08-17"
BUILD, NEWS = "構築記録", "収集と考察"
PILLAR_CLASS = {BUILD: "p-build", NEWS: "p-news"}

NAV = ('<nav class="nav"><a href="{r}"{c1}>記録</a>'
       '<a href="{r}rinji.html"{c2}>稟議</a>'
       '<a href="{r}about.html"{c3}>このサイトについて</a></nav>')

SITE = "https://lab.sky-social.com"

TPL = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — SKY SOCIAL LAB</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="SKY SOCIAL LAB">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site}/articles/og/{no}.png?v={ver}">
<meta property="og:url" content="{site}/articles/{no}.html">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../style.css">
</head>
<body class="{pcls}">

<header><div class="hd">
  <a href="../" class="logo">SKY SOCIAL LAB</a>
  {nav}
</div></header>

<div class="wrap">
<article>
  <div class="a-head">
    <img class="hband" src="og/{no}.png?v={ver}" alt="" width="1200" height="630">
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

  <div class="stampbox" data-rinji="{rinji}">
    <div class="stampinfo">稟議番号　<em>{rinji}</em><br>決裁の記録を読み込んでいます…</div>
  </div>

  <p class="disclosure">この記事はAIが起案し、人間が内容を確認・承認したうえで公開しています。上の決裁欄は台帳 <code>ledger/rinji.json</code> をそのまま表示しています。事実関係の誤りが判明した場合は、修正内容を明記したうえで訂正します。</p>
</article>
</div>

<footer><div class="ft">
  <span>SKY SOCIAL LAB</span>
  <span><a href="https://www.sky-social.com">SKY SOCIAL株式会社</a></span>
</div></footer>

<script src="../site.js"></script>
</body>
</html>
"""

LEAD = """  <a class="entry p-build lead-art" href="{file}">
    <img class="card-thumb" src="articles/og/{no}.png?v={ver}" alt="" width="1200" height="630">
    <div class="ebody">
      <div class="erow"><span class="eno">No.{no}</span><span class="pillar">構築記録</span></div>
      <div class="etitle">{title}</div>
      <div class="elead">{lead}</div>
      <div class="edate">{date} ／ 稟議 {rinji}</div>
    </div>
  </a>
"""

SUB = """    <a class="entry p-build" href="{file}">
      <img class="card-thumb" src="articles/og/{no}.png?v={ver}" alt="" width="1200" height="630">
      <div class="ebody">
        <div class="erow"><span class="eno">No.{no}</span></div>
        <div class="etitle">{title}</div>
        <div class="edate">{date}</div>
      </div>
    </a>
"""

DIG = """  <a class="dig" href="{file}">
    <img class="card-thumb" src="articles/og/{no}.png?v={ver}" alt="" width="1200" height="630">
    <div class="dbody">
      <span class="d">{date}</span>
      <div class="t">{title}</div>
      <div class="s">{sources}</div>
    </div>
  </a>
"""

INDEX = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SKY SOCIAL LAB — AIだけで会社をつくる記録</title>
<meta name="description" content="記事はAIが書き、人間が承認して公開する。承認していないものは公開されない。中小企業のバックオフィスをAIで作れるのかを、失敗も含めて記録しています。">
<link rel="stylesheet" href="style.css">
</head>
<body>

<header><div class="hd">
  <a href="./" class="logo">SKY SOCIAL LAB</a>
  {nav}
</div></header>

<div class="wrap">

<section class="hero">
  <h1>AIだけで会社をつくる、<br>その全部を記録する。</h1>
  <p>ここに出ている記事は、すべてAIが書いています。人間がすることは、公開してよいかを決めることだけです。うまくいったことも、外れた判断も、消さずに残します。中小企業のバックオフィスをAIで作れるのか——その検証の記録です。</p>

  <div class="flow">
    <div><span class="n">01</span><span class="t">起案</span><span class="w">AIが書く</span></div>
    <div><span class="n">02</span><span class="t">承認</span><span class="w me">人間が決める</span></div>
    <div><span class="n">03</span><span class="t">公開</span><span class="w">承認したものだけ</span></div>
  </div>

  <div class="stats">
    <span>記録 <b>{total}</b> 件</span>
    <span>承認済 <b id="s-ok">—</b> 件</span>
    <span class="w">承認待ち <b id="s-wait">—</b> 件</span>
    <span>運営開始 <b>{since}</b></span>
    <span>広告なし</span>
  </div>
</section>

<div class="zhead">
  <h2>構築記録</h2>
  <span class="z">自分たちが何を、どう決めたか</span>
  <span class="c">{n_build}件</span>
</div>
{build}
<div class="zhead">
  <h2>収集と考察</h2>
  <span class="z">外で何が起きているか</span>
  <span class="c">{n_news}件</span>
</div>
{news}
</div>

<footer><div class="ft">
  <span>SKY SOCIAL LAB</span>
  <span><a href="https://www.sky-social.com">SKY SOCIAL株式会社</a></span>
</div></footer>

<script src="site.js"></script>
</body>
</html>
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


def nav(root: str, page: str) -> str:
    return NAV.format(r=root,
                      c1=' aria-current="page"' if page == "index" else "",
                      c2=' aria-current="page"' if page == "rinji" else "",
                      c3=' aria-current="page"' if page == "about" else "")


def source_line(collected: dict) -> str:
    """その日に見た情報源。記事の中身ではなく、見に行った先を示す。"""
    items = collected.get("items", [])
    if not items:
        return ""
    seen, names = set(), []
    for i in items:
        s = (i.get("source") or "").strip()
        if s and s not in seen:
            seen.add(s)
            names.append(s)
    if not names:
        return ""
    head = "・".join(names[:3])
    rest = f" ほか{len(items)}件" if len(items) > 3 else f" {len(items)}件"
    return f"この日見た情報源　{head}{rest}"


def build_index(arts) -> None:
    """トップページを台帳から組み直す。継ぎ足しではなく毎回作りなおす。"""
    rows = sorted(arts["articles"], key=lambda a: str(a.get("no", "")), reverse=True)
    e = html.escape

    def date_of(a):
        return e(a.get("published_at") or a.get("drafted_at") or "")

    def og_ver(no):
        og_path = f"articles/og/{no}.png"
        return og_image.file_hash(og_path) if os.path.exists(og_path) else "0"

    builds = [a for a in rows if a.get("pillar") == BUILD]
    news = [a for a in rows if a.get("pillar") == NEWS]

    parts = []
    if builds:
        h = builds[0]
        parts.append(LEAD.format(file=e(h.get("file", "")), no=e(str(h.get("no", ""))),
                                 title=e(h.get("title", "")), lead=e(h.get("lead", "")),
                                 date=date_of(h), rinji=e(h.get("rinji", "")),
                                 ver=og_ver(h.get("no", ""))))
        if builds[1:]:
            parts.append('  <div class="sub">\n')
            for a in builds[1:]:
                parts.append(SUB.format(file=e(a.get("file", "")),
                                        no=e(str(a.get("no", ""))),
                                        title=e(a.get("title", "")), date=date_of(a),
                                        ver=og_ver(a.get("no", ""))))
            parts.append("  </div>\n")
    else:
        parts.append('  <p class="empty">まだありません。</p>\n')

    dig = "".join(
        DIG.format(file=e(a.get("file", "")), no=e(str(a.get("no", ""))), date=date_of(a),
                   title=e(a.get("title", "")), sources=e(a.get("sources", "")),
                   ver=og_ver(a.get("no", "")))
        for a in news) or '  <p class="empty">まだありません。</p>\n'

    open("index.html", "w", encoding="utf-8").write(INDEX.format(
        nav=nav("./", "index"), since=SINCE, total=len(rows),
        n_build=len(builds), n_news=len(news),
        build="".join(parts), news=dig))
    print(f"  トップページを組み直しました（構築記録{len(builds)}件／収集と考察{len(news)}件）")


def main() -> int:
    arts = load("ledger/articles.json", {"articles": []})

    if "--index" in sys.argv:
        build_index(arts)
        return 0

    drafts = load(WORK, {}).get("drafts", [])
    if not drafts:
        print("起案された記事がありません。何もしません。")
        return 0

    today = datetime.now(JST).strftime("%Y-%m-%d")
    rin = load("ledger/rinji.json", {"rinji": []})
    nip = load("ledger/nippou.json", {"days": []})
    srcline = source_line(load(COLLECTED, {}))

    made = []
    for d in drafts:
        no = next_no(arts["articles"])
        rno = next_rinji(rin["rinji"])
        title, pillar = d["title"], d["pillar"]

        og_path = og_image.make(no, title, pillar, rno)
        ver = og_image.file_hash(og_path)

        page = TPL.format(
            title=html.escape(title), desc=html.escape(d["lead"]),
            no=no, pillar=html.escape(pillar), site=SITE, ver=ver,
            pcls=PILLAR_CLASS.get(pillar, ""), nav=nav("../", ""),
            lead=html.escape(d["lead"]), body=d["body"], rinji=rno)

        os.makedirs("articles", exist_ok=True)
        open(f"articles/{no}.html", "w", encoding="utf-8").write(page)

        arts["articles"].insert(0, {
            "no": no, "file": f"articles/{no}.html", "pillar": pillar,
            "title": title, "lead": d["lead"],
            "sources": srcline if pillar == NEWS else "",
            "drafted_by": "Claude", "drafted_at": today,
            "rinji": rno, "published_at": None, "status": "pending"})

        rin["rinji"].append({
            "no": rno, "subject": f"記事 No.{no} を公開する",
            "detail": f"「{title}」を公開します。",
            "proposed_by": "Claude", "proposed_at": today,
            "status": "pending", "approved_by": None, "approved_at": None,
            "article": f"articles/{no}.html"})

        made.append({"no": no, "rinji": rno, "title": title})
        print(f"  No.{no}  {rno}  {title}")

    build_index(arts)

    day = next((x for x in nip["days"] if x["date"] == today), None)
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
