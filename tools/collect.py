#!/usr/bin/env python3
"""
公開情報の収集

feeds.json に記載された公式RSSのみを取得する。
スクレイピングは行わない。取得先を増やす場合も、公式が配信しているものに限る。

結果は work/collected.json に書き出す。
"""
import json, os, sys, re, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

JST = timezone(timedelta(hours=9))
CONFIG = "feeds.json"
OUT_DIR = "work"
OUT = os.path.join(OUT_DIR, "collected.json")
SEEN = "ledger/seen.json"

UA = "sky-lab/1.0 (+https://lab.sky-social.com)"
TIMEOUT = 20
BODY_MAX_CHARS = 6000
BODY_MIN_CHARS = 200


def fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
    except Exception as e:
        print(f"    取得できませんでした: {type(e).__name__}")
        return None
    for enc in ("utf-8", "shift_jis", "euc-jp"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


class _TextExtractor(HTMLParser):
    """HTMLから本文らしきテキストだけを拾う簡易版。外部ライブラリは使わない。"""

    SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth == 0:
            text = data.strip()
            if text:
                self.chunks.append(text)


def fetch_article_body(url: str) -> str | None:
    """記事ページ本文を取得する。取れない・短すぎる場合は None（見出しのみ扱いにする）。"""
    if not url:
        return None
    html = fetch(url)
    if not html:
        return None
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return None
    text = re.sub(r"\n{2,}", "\n", "\n".join(parser.chunks)).strip()
    if len(text) < BODY_MIN_CHARS:
        return None
    return text[:BODY_MAX_CHARS]


def parse(xml_text: str) -> list[dict]:
    """RSS 1.0 / 2.0 / Atom のいずれでも item を拾う。"""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        print("    形式を解釈できませんでした")
        return []

    items = []
    for el in root.iter():
        if strip_ns(el.tag) not in ("item", "entry"):
            continue
        rec = {"title": "", "link": "", "date": ""}
        for child in el:
            name = strip_ns(child.tag)
            if name == "title" and child.text:
                rec["title"] = child.text.strip()
            elif name == "link":
                rec["link"] = (child.text or child.get("href") or "").strip()
            elif name in ("date", "pubDate", "published", "updated") and child.text:
                if not rec["date"]:
                    rec["date"] = child.text.strip()
        if rec["title"]:
            items.append(rec)
    return items


def load_seen() -> set:
    if not os.path.exists(SEEN):
        return set()
    try:
        return set(json.load(open(SEEN, encoding="utf-8")).get("links", []))
    except Exception:
        return set()


def save_seen(seen: set) -> None:
    os.makedirs("ledger", exist_ok=True)
    keep = list(seen)[-3000:]
    json.dump({"note": "既読の記録。同じ話題を繰り返し扱わないために使う。",
               "links": keep},
              open(SEEN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main() -> int:
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    kw_ja = cfg.get("keywords_ja", cfg.get("keywords", []))
    kw_en = cfg.get("keywords_en", [])
    limit = cfg.get("max_items", 14)
    seen = load_seen()

    print(f"公開情報の収集　{datetime.now(JST):%Y-%m-%d %H:%M}\n")

    picked, checked = [], 0
    for f in cfg.get("feeds", []):
        if not f.get("enabled") or not f.get("url"):
            print(f"  — {f['name']}（未設定。飛ばします）")
            continue
        print(f"  [{f.get('category','')}] {f['name']}")
        text = fetch(f["url"])
        if not text:
            continue
        items = parse(text)
        checked += len(items)
        print(f"    {len(items)}件を確認")

        per_max = f.get("max", 4)
        taken = 0
        for it in items:
            if taken >= per_max:
                break
            if it["link"] and it["link"] in seen:
                continue
            title = it["title"]
            low = title.lower()
            hit = [k for k in kw_ja if k in title]
            hit += [k for k in kw_en if k.lower() in low and k not in hit]
            if not hit:
                continue
            it["source"] = f["name"]
            it["category"] = f.get("category", "")
            it["matched"] = hit[:5]
            picked.append(it)
            taken += 1
            if it["link"]:
                seen.add(it["link"])

    picked = picked[:limit]

    print(f"\n  本文を取得中（{len(picked)}件）")
    got_body = 0
    for it in picked:
        body = fetch_article_body(it["link"])
        it["body"] = body
        if body:
            got_body += 1
        else:
            print(f"    本文なしで進めます（見出しのみ扱い）: {it['title'][:48]}")
    print(f"  本文を取得できた記事: {got_body}/{len(picked)}件")

    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump({
        "collected_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "checked": checked,
        "picked": len(picked),
        "items": picked,
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    save_seen(seen)

    print(f"\n  確認 {checked}件 → 該当 {len(picked)}件")
    by_cat = {}
    for it in picked:
        by_cat.setdefault(it.get("category", ""), []).append(it)
    for cat, xs in by_cat.items():
        print(f"\n  [{cat}]")
        for it in xs:
            print(f"    ・{it['title'][:64]}")
    if not picked:
        print("\n  本日は該当がありませんでした。考察記事は作成しません。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
