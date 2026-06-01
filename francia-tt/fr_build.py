#!/usr/bin/env python3
"""Build FR dataset for PSG-final riots event (30 May 2026)."""
import json, os, re
from datetime import datetime

TR_DIR = "/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results"
FILES = [
    "mcp-snare-x-tw_search-1780313060786.txt",
    "mcp-snare-x-tw_search-1780313199461.txt",
    "mcp-snare-x-tw_search-1780313267926.txt",
    "mcp-snare-x-tw_search-1780313443138.txt",
    "mcp-snare-x-tw_search-1780313487399.txt",
    "mcp-snare-x-tw_search-1780313935013.txt",
    "mcp-snare-x-tw_search-1780313957223.txt",
    "mcp-snare-x-tw_search-1780313976494.txt",
]
OUT_RAW = "/Users/pinperepette/Github/postmortem/francia-tt/fr_dataset_raw.json"


def load_file(path):
    raw = open(path, encoding="utf-8").read()
    try:
        d = json.loads(raw)
    except Exception:
        dec = json.JSONDecoder()
        i = raw.find("{")
        d, _ = dec.raw_decode(raw[i:])
    # list[0]['text'] -> inner json
    if isinstance(d, list):
        if d and isinstance(d[0], dict) and "text" in d[0] and "tweets" not in d[0]:
            try:
                inner = json.loads(d[0]["text"])
                return inner.get("tweets", []) if isinstance(inner, dict) else inner
            except Exception:
                pass
        return d
    if isinstance(d, dict):
        if "tweets" in d:
            return d["tweets"]
    return []


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


HASHTAG_RE = re.compile(r"#(\w+)")
CUTOFF = datetime.fromisoformat("2026-05-29T00:00:00+00:00")

# on-topic keywords (riot/violence context tied to PSG final)
ON_KW = [
    "émeute", "emeute", "casseur", "voiture", "feu", "incendi", "violenc",
    "pillage", "saccag", "ratonnade", "racaille", "ensauvag", "banlieue",
    "fan zone", "fanzone", "champs", "arrest", "interpell", "blessé", "blesse",
    "mort", "police", "crs", "gendarm", "psg", "finale", "ligue des champions",
    "champions league", "paris", "commune", "tué", "tue", "couvre-feu",
    "immigr", "remplac", "juif", "barbar", "sauvage", "macron",
]
# off-topic / pure sport indicators (only drop if no riot kw)
SPORT_ONLY = ["but de", "gardien", "compo", "transfert", "mercato", "score", "match nul"]


def is_on_topic(t):
    txt = (t.get("text") or "").lower()
    dt = parse_date(t.get("created_at"))
    lang = (t.get("lang") or "").lower()
    if lang != "fr":
        return False
    if dt is None or dt < CUTOFF:
        return False
    has_on = any(k in txt for k in ON_KW)
    if not has_on:
        return False
    # require riot/violence context, not pure sport celebration of score
    riot_kw = ["émeute", "emeute", "casseur", "voiture", "feu", "incendi", "violenc",
               "pillage", "saccag", "ratonnade", "racaille", "ensauvag", "arrest",
               "interpell", "blessé", "blesse", "mort", "police", "crs", "barbar",
               "sauvage", "couvre-feu", "immigr", "remplac", "juif", "commune",
               "tué", "banlieue", "ratonn", "guerre"]
    if not any(k in txt for k in riot_kw):
        return False
    return True


def followers_of(t):
    a = t.get("author") or {}
    return a.get("followers", 0) or 0


def record(t):
    a = t.get("author") or {}
    m = t.get("metrics") or {}
    media = t.get("media") or []
    mt = media[0].get("type") if media else None
    txt = t.get("text") or ""
    likes = m.get("likes", 0) or 0
    rts = m.get("retweets", 0) or 0
    rep = m.get("replies", 0) or 0
    qts = m.get("quotes", 0) or 0
    return {
        "id": str(t.get("id")),
        "url": t.get("url"),
        "handle": a.get("handle"),
        "name": a.get("name"),
        "verified": a.get("verified", False),
        "followers": followers_of(t),
        "date": t.get("created_at"),
        "text": txt,
        "likes": likes,
        "retweets": rts,
        "replies": rep,
        "quotes": qts,
        "views": m.get("views", 0) or 0,
        "media_type": mt,
        "is_quote": bool(t.get("quoted_tweet")),
        "hashtags": HASHTAG_RE.findall(txt),
        "engagement": likes + rts + rep + qts,
    }


def main():
    seen = {}  # id -> record (keep max likes)
    total_parsed = 0
    for fn in FILES:
        tweets = load_file(os.path.join(TR_DIR, fn))
        for t in tweets:
            if not isinstance(t, dict):
                continue
            cands = [t]
            q = t.get("quoted_tweet")
            if isinstance(q, dict):
                cands.append(q)
            for c in cands:
                total_parsed += 1
                if not is_on_topic(c):
                    continue
                rid = str(c.get("id"))
                rec = record(c)
                if rid not in seen or rec["likes"] > seen[rid]["likes"]:
                    seen[rid] = rec
    data = sorted(seen.values(), key=lambda r: r["likes"], reverse=True)
    json.dump(data, open(OUT_RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("parsed_candidates", total_parsed)
    print("on_topic_unique", len(data))
    dates = [r["date"] for r in data if r["date"]]
    print("date_min", min(dates), "date_max", max(dates))
    print("written", OUT_RAW)


if __name__ == "__main__":
    main()
