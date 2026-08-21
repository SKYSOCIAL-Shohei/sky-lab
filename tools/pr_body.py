#!/usr/bin/env python3
"""
プルリクエストの表題と本文を組み立てる。

対象は「本日この起案で起票した稟議」だけに限る。
承認待ちを全部拾うと、過去に承認されないまま残っているものが表題に混ざり、
承認した瞬間にそれらまで承認済みとして記録されてしまう。
承認は、いま中身を確認したものにだけ及ぶべきである。

過去の未承認は、承認の対象にはせず、本文の末尾で警告として知らせる。
"""
import json, sys, os
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def main() -> int:
    r = json.load(open("ledger/rinji.json", encoding="utf-8"))["rinji"]
    pending = [x for x in r if x.get("status") == "pending"]
    date = datetime.now(JST).strftime("%Y-%m-%d")

    # 本日起票したものだけを、この申請の対象とする
    mine = [x for x in pending if x.get("proposed_at") == date]
    older = [x for x in pending if x.get("proposed_at") != date]

    if not mine:
        print("本日起票した稟議がありません。", file=sys.stderr)
        return 1

    nos = " ".join(x["no"] for x in mine)
    title = f"{nos} {date} の起案"

    lines = [
        "AIが起案しました。内容を確認のうえ、承認してください。",
        "",
        "| 稟議 | 内容 |",
        "|---|---|",
    ]
    lines += [f"| {x['no']} | {x['subject']} |" for x in mine]
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

    # 承認されないまま残っているものを知らせる。承認の対象には含めない。
    if older:
        lines += [
            "",
            "---",
            "",
            "### 承認されていない稟議が残っています",
            "",
            f"過去の起案のうち、承認を経ないまま {len(older)} 件が残っています。",
            "記事がすでに公開されている場合、それは承認前に公開されたことを意味します。",
            "",
        ]
        lines += [
            f"- 稟議 {x['no']}（{x.get('proposed_at') or '日付不明'} 起票）　{x['subject']}"
            for x in older
        ]
        lines += [
            "",
            "**この申請を承認しても、上記は承認されません。**",
            "対象は表題に並んだ稟議だけです。",
            "",
            "公開済みのものは後から承認できません。稟議一覧に経緯を残してください。",
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
