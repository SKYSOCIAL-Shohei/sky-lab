#!/usr/bin/env python3
"""
事後承認PRの下準備

限定的事後承認（AGENTS.md）の対象になるのは「収集と考察」だけである。
「構築記録」を誤って対象にしないよう、ここで機械的に弾く。

対象の稟議がすべて次を満たすことを確認したうえで、日報に記録する。
  - 稟議が実在する
  - まだ承認されていない（status が approved でない）
  - 対応する記事の pillar が「収集と考察」

  使い方:  python3 tools/posthoc_approve.py R-0012 R-0013 -- 「理由」
"""
import json, os, sys, datetime

LEDGER = "ledger/rinji.json"
ARTICLES = "ledger/articles.json"
NIPPOU = "ledger/nippou.json"
JST = datetime.timezone(datetime.timedelta(hours=9))


def main() -> int:
    args = sys.argv[1:]
    if "--" not in args:
        print("使い方: posthoc_approve.py R-0012 R-0013 -- 理由")
        return 1
    sep = args.index("--")
    nos, note = args[:sep], " ".join(args[sep + 1:]) or "（理由未記入）"
    if not nos:
        print("対象の稟議番号がありません。")
        return 1

    rinji = {x["no"]: x for x in json.load(open(LEDGER, encoding="utf-8"))["rinji"]}
    articles = {a.get("rinji"): a for a in json.load(open(ARTICLES, encoding="utf-8"))["articles"]}

    errors = []
    for no in nos:
        r = rinji.get(no)
        if r is None:
            errors.append(f"{no}: 台帳に存在しません")
            continue
        if r.get("status") == "approved":
            errors.append(f"{no}: 既に承認済みです")
            continue
        a = articles.get(no)
        if a is None:
            errors.append(f"{no}: 対応する記事が見つかりません")
            continue
        if a.get("pillar") != "収集と考察":
            errors.append(
                f"{no}: pillar が「{a.get('pillar')}」です。"
                f"事後承認の対象は「収集と考察」に限られます。構築記録は対象外です。"
            )

    if errors:
        print("事後承認の対象として不適格です：")
        for e in errors:
            print(f"  - {e}")
        return 1

    today = datetime.datetime.now(JST).strftime("%Y-%m-%d")
    nip = json.load(open(NIPPOU, encoding="utf-8"))
    day = next((x for x in nip["days"] if x["date"] == today), None)
    if day is None:
        day = {"date": today, "entries": []}
        nip["days"].insert(0, day)
    day["entries"].append({
        "time": "—", "who": "人間",
        "what": f"{', '.join(nos)} の事後承認PRを作成（理由: {note}）",
    })
    json.dump(nip, open(NIPPOU, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"対象：{', '.join(nos)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
