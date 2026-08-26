#!/usr/bin/env python3
"""
市場調査エージェント

株主であるSKY SOCIAL株式会社の会社概要を材料に、AIだけで開発・運営できそうな
新規事業の候補領域をClaudeに考えさせ、「構築記録」の草稿を1本作る。

会社概要は work/company_profile.md（.gitignore対象、社外秘）から読む。このファイルは
リポジトリに含めていないため、GitHub Actions上では実行できない。現時点では、手元で
対話的に実行することを想定したオンデマンドのツール（毎日回すものではない）。

数字は作らない（AGENTS.md 8節）。出典のない市場規模・成長率などは書かない。
このスクリプト自身は事業を始める判断をしない。候補を挙げて人間の判断に委ねるだけ。
会社概要そのもの（取引先名・資本金・正確な所在地・内部ロードマップの固有名など）は
社外秘のため、生成する記事には具体的に書かせない。

  使い方:  python3 tools/research.py
  必要な環境変数:  ANTHROPIC_API_KEY
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
import write as W

JST = timezone(timedelta(hours=9))
PROFILE_PATH = "work/company_profile.md"
WORK = "work"

CONFIDENTIALITY_NOTE = """
【会社概要の扱い（重要）】
渡す会社概要は社外秘であり、その内容を引用・要約して記事に書いてはいけない。
書いてよいのは一般化した業種・地域・立ち位置（例：「地方でDX支援を行う会社」程度）まで。
具体的な取引先名、資本金の額、正確な所在地、内部ロードマップの固有名、
代表者・取締役の経歴の詳細は、記事に一切書かないこと。
"""


def write_research(profile: str) -> dict | None:
    system = ("あなたはSKY SOCIAL LABの記録係です。AIだけで新規事業を作れるかを検証する"
              "事業の一環として、市場調査を始めます。" + CONFIDENTIALITY_NOTE + W.RULES)
    user = f"""以下は株主であるSKY SOCIAL株式会社の会社概要（社外秘、記事には具体的に書かないこと）です。

{profile}

これを踏まえて、AIだけで開発・運営できそうな新規事業の候補領域を3〜5個考え、
構築記録の記事を1本書いてください。

要件:
- 候補は、株主の既存事業と直接競合・共食いしない方向を優先する
- 一方で、株主が持つ地域・業種の土地勘や顧客接点を活かせる案があれば歓迎する
- それぞれの候補について、なぜAIだけで作れそうか、なぜ検討する価値がありそうかを書く
- 市場規模・成長率などの数字は一切作らない。出典のない数字を書かない
- どれが良いかを決めつけず、比較検討の材料として複数案を並べる。最終判断は人間に委ねる
- 会社概要そのものの引用・要約はしない。一般化した言葉で書く
- 1,500〜2,200字程度
- 本文で使ってよいタグは h2, p, strong, ul, li のみ

{W.FORMAT}"""

    out = W.parse_out(W.call(system, user, max_tokens=4000), "research")
    if out:
        out["pillar"] = "構築記録"
    return out


def main() -> int:
    if not os.path.exists(PROFILE_PATH):
        print(f"{PROFILE_PATH} が見つかりません。")
        print("このツールは会社概要（社外秘）をもとに動くため、work/配下に")
        print("company_profile.md を用意してから実行してください。")
        print("GitHub Actionsでは実行できません（このファイルはリポジトリに含めていません）。")
        return 1

    profile = open(PROFILE_PATH, encoding="utf-8").read()
    print(f"市場調査　{datetime.now(JST):%Y-%m-%d %H:%M}\n")

    try:
        d = write_research(profile)
    except Exception as e:
        print(f"作成できませんでした: {e}")
        return 1
    if not d:
        return 1

    print(f"「{d['title']}」　本文{len(d['body'])}字\n")

    path = os.path.join(WORK, "drafts.json")
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"drafts": []}
    data["drafts"].append(d)
    os.makedirs(WORK, exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{path} に追加しました。次は python3 tools/publish.py で記事化してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
