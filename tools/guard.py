#!/usr/bin/env python3
"""
公開前セキュリティ検査

公開されるすべてのファイルを走査し、外に出してはいけない情報が
含まれていないか検査する。1件でも見つかれば異常終了する。

人の目視ではなく、この検査を通過したものだけを公開する。

  使い方:  python3 tools/guard.py
  終了コード:  0 = 合格 / 1 = 不合格（公開してはいけない）
"""
import re, sys, json, glob, os

# ── 公開対象（ここに列挙されたものだけが公開される想定） ──
TARGETS = ["*.html", "articles/*.html", "ledger/*.json", "*.css"]

# ── サイト自身の公開URLは許可 ──
ALLOW = {"lab.sky-social.com", "www.sky-social.com", "sky-social.com"}

RULES = [
    # (重大度, 名称, 正規表現, 説明)
    ("BLOCK", "IPアドレス",
     r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
     "サーバーの所在が特定される"),

    ("BLOCK", "ホスト名",
     r"\b[a-z0-9][a-z0-9-]*\.(?:[a-z0-9-]+\.)*sky-social\.com\b",
     "存在するホストは偵察の起点になる"),

    ("BLOCK", "DNSレコード値",
     r"\b(?:CNAME|MX|TXT|NS|AAAA)\s*[:：=]|\bv=spf1|\bv=DKIM1|\bp=MII",
     "メール認証やDNS構成が特定される"),

    ("BLOCK", "所有権確認トークン",
     r"site-verification|\bMS=ms\d+|_domainkey",
     "第三者に所有権を主張される恐れ"),

    ("BLOCK", "認証情報",
     r"(?i)\b(?:api[_-]?key|secret|password|passwd|token|bearer|private[_-]?key)\b\s*[:=]"
     r"|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN",
     "認証情報の漏洩"),

    ("BLOCK", "内部ホスティング名",
     r"(?i)\b(?:webaccel|\.sakura\.ne\.jp|mail\.protection\.outlook|autodiscover|\.pages\.dev)\b",
     "利用構成が特定される"),

    ("WARN", "事業者名",
     r"(?i)\b(?:Cloudflare|GitHub|さくらインターネット|Microsoft\s?365)\b",
     "構成の推測材料になる。判断の記録として必要か再考すること"),

    ("WARN", "ファイルパス",
     r"(?:/(?:etc|var|home|root|Users)/[a-zA-Z0-9._/-]{3,})",
     "内部構成の露出"),
]


def collect():
    files = []
    for pat in TARGETS:
        files += glob.glob(pat)
    return sorted(set(f for f in files if os.path.isfile(f)))


def scan(path):
    text = open(path, encoding="utf-8").read()
    found = []
    for sev, name, pat, why in RULES:
        for m in re.finditer(pat, text):
            hit = m.group(0)
            if hit in ALLOW:
                continue
            if name == "ホスト名" and hit in ALLOW:
                continue
            line = text[:m.start()].count("\n") + 1
            found.append((sev, name, hit, line, why))
    return found


def main():
    files = collect()
    if not files:
        print("公開対象ファイルが見つかりません。リポジトリの直下で実行してください。")
        return 1

    blocks, warns = [], []
    print(f"公開前セキュリティ検査 — 対象 {len(files)} ファイル\n")

    for f in files:
        hits = scan(f)
        if not hits:
            print(f"  OK    {f}")
            continue
        b = [h for h in hits if h[0] == "BLOCK"]
        w = [h for h in hits if h[0] == "WARN"]
        mark = "BLOCK" if b else "WARN "
        print(f"  {mark} {f}")
        for sev, name, hit, line, why in hits:
            shown = hit if len(hit) <= 40 else hit[:37] + "..."
            print(f"        L{line} [{name}] {shown}")
            print(f"              → {why}")
        blocks += [(f, *h[1:]) for h in b]
        warns += [(f, *h[1:]) for h in w]

    # JSONの構文も検査する（台帳が壊れていれば画面が動かない）
    for f in glob.glob("ledger/*.json"):
        try:
            json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"\n  BLOCK {f} — JSONが壊れています: {e}")
            blocks.append((f, "JSON構文", str(e), 0, "台帳が読めない"))

    print()
    if blocks:
        print(f"不合格：{len(blocks)}件の要修正。公開してはいけません。")
        return 1
    if warns:
        print(f"合格（警告 {len(warns)}件）。内容を確認のうえ判断してください。")
        return 0
    print("合格：外に出してはいけない情報は見つかりませんでした。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
