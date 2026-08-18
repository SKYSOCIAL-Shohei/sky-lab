#!/usr/bin/env python3
"""プルリクエストの表題と本文を組み立てる。"""
import json, sys, os
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

def main() -> int:
    r = json.load(open("ledger/rinji.json", encoding="utf-8"))["rinji"]
    pending = [x for x in r if x.get("status") == "pending"]
    if not pending:
        print("承認待ちの稟議がありません。", file=sys.stderr)
        return 1

    date = datetime.now(JST).strftime("%Y-%m-%d")
    nos = " ".join(x["no"] for x in pending)
    title = f"{nos} {date} の起案"

    lines = [
        "AIが起案しました。内容を確認のうえ、承認してください。",
        "",
        "| 稟議 | 内容 |",
        "|---|---|",
    ]
    lines += [f"| {x['no']} | {x['subject']} |" for x in pending]
    lines += [
        "",
        "検査は2種類とも通過しています。",
        "",
        "- 情報漏れの検査",
        "- 未承認公開の検査",
        "",
        "承認すると、承認者と時刻が台帳へ自動で記録されます。",
        "差し戻す場合は Request changes を選んでください。",
    ]

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"title={title}\n")
            f.write("body<<PRBODY\n" + "\n".join(lines) + "\nPRBODY\n")
    else:
        print(title)
        print("---")
        print("\n".join(lines))
    return 0

if __name__ == "__main__":
    sys.exit(main())
