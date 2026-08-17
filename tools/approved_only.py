#!/usr/bin/env python3
"""
未承認公開の検査

台帳上「承認済み」になっていない稟議の対象物が、公開されようとしていないか調べる。

承認していないものが世に出ることを防ぐための検査であり、
guard.py（情報漏れの検査）とは目的が異なる。

  使い方:  python3 tools/approved_only.py
  終了コード:  0 = 合格 / 1 = 不合格
"""
import json, sys, os, re

LEDGER = "ledger/rinji.json"
ARTICLES = "ledger/articles.json"


def main() -> int:
    if not os.path.exists(LEDGER):
        print("稟議台帳が見つかりません。")
        return 1

    rinji = json.load(open(LEDGER, encoding="utf-8")).get("rinji", [])
    state = {x["no"]: x.get("status") for x in rinji}

    problems = []

    # 記事台帳で「公開済み」とされているものは、対応する稟議が承認済みであること
    if os.path.exists(ARTICLES):
        for a in json.load(open(ARTICLES, encoding="utf-8")).get("articles", []):
            if a.get("status") != "published":
                continue
            no = a.get("rinji")
            if not no:
                problems.append(f"記事 No.{a.get('no')} に稟議番号がありません")
                continue
            if state.get(no) != "approved":
                problems.append(
                    f"記事 No.{a.get('no')} は公開済みですが、稟議 {no} が"
                    f"{state.get(no) or '台帳になし'} です")

    # 稟議の状態と承認欄の整合を調べる
    for x in rinji:
        no, st = x["no"], x.get("status")
        by, at = x.get("approved_by"), x.get("approved_at")
        if st == "approved" and not (by and at):
            problems.append(f"{no} は承認済みですが、承認者または時刻が空です")
        if st != "approved" and (by or at):
            problems.append(f"{no} は未承認ですが、承認欄に記入があります")

    # 番号の欠落を調べる
    nums = sorted(int(m.group(1)) for x in rinji
                  if (m := re.match(r"R-(\d+)$", x["no"])))
    if nums:
        gaps = [i for i in range(nums[0], nums[-1] + 1) if i not in nums]
        if gaps:
            problems.append(
                "稟議番号に欠番があります: " + ", ".join(f"R-{i:04d}" for i in gaps))

    print("未承認公開の検査\n")
    for x in rinji:
        mark = "承認済" if x.get("status") == "approved" else "未承認"
        who = x.get("approved_by") or "—"
        print(f"  {x['no']}  [{mark}]  承認者 {who}")

    print()
    if problems:
        print(f"不合格：{len(problems)}件\n")
        for p in problems:
            print(f"  ・{p}")
        print("\n承認されていないものは公開できません。")
        return 1

    print("合格：公開済みのものは、すべて承認を経ています。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
