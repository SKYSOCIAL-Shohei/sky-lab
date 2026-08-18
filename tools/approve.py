#!/usr/bin/env python3
"""
承認の記録

プルリクエストが承認されたとき、承認者と時刻を台帳へ書き込む。

承認者名はGitHubが渡す値のみを使う。本文から読み取ることはしない。
AIが「誰が承認したか」を書けない構造にするための制約である。
"""
import os, re, sys, json, datetime

LEDGER = "ledger/rinji.json"


def target_numbers(title: str, body: str) -> list[str]:
    """PRの表題と本文から稟議番号を拾う。表題を優先する。"""
    pat = re.compile(r"\bR-\d{4}\b")
    nos = pat.findall(title or "")
    if not nos:
        nos = pat.findall(body or "")
    # 重複を除き、出現順を保つ
    seen, out = set(), []
    for n in nos:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def to_jst(iso: str) -> str:
    """GitHubのUTC時刻を日本時間の表記に直す。"""
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        jst = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
        return jst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso or ""


def main() -> int:
    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "")
    reviewer = os.environ.get("REVIEWER", "").strip()
    at = to_jst(os.environ.get("REVIEWED_AT", ""))

    if not reviewer:
        print("承認者が取得できませんでした。台帳は変更しません。")
        return 1

    nos = target_numbers(title, body)
    if not nos:
        print("稟議番号が見つかりません。PRの表題に R-0001 の形式で記載してください。")
        print("台帳は変更しません。")
        return 0

    data = json.load(open(LEDGER, encoding="utf-8"))
    index = {x["no"]: x for x in data.get("rinji", [])}

    changed = []
    for no in nos:
        item = index.get(no)
        if item is None:
            print(f"  {no} は台帳にありません。飛ばします。")
            continue
        if item.get("status") == "approved":
            print(f"  {no} は既に承認済みです。上書きしません。")
            continue
        item["status"] = "approved"
        item["approved_by"] = reviewer
        item["approved_at"] = at
        item.pop("note", None)
        changed.append(no)
        print(f"  {no} を承認済みにしました（承認者 {reviewer} / {at}）")

    if not changed:
        print("更新対象がありませんでした。")
        return 0

    json.dump(data, open(LEDGER, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 承認された稟議に対応する記事を、公開済みへ切り替える
    ARTICLES = "ledger/articles.json"
    if os.path.exists(ARTICLES):
        arts = json.load(open(ARTICLES, encoding="utf-8"))
        moved = []
        for a in arts.get("articles", []):
            if a.get("rinji") in changed and a.get("status") != "published":
                a["status"] = "published"
                a["published_at"] = at.split(" ")[0] if at else None
                moved.append(a.get("no"))
        if moved:
            json.dump(arts, open(ARTICLES, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"記事を公開済みにしました：No.{', No.'.join(moved)}")

    print(f"\n台帳を更新しました：{', '.join(changed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
