#!/usr/bin/env python3
"""
Twitter account analysis for @nessunodalnulla (Lo Stimatore)
Source: MongoDB SnareData.twitter
Stessa pipeline di pinassi-postmortem: KPI organici + RT interest graph + diagnostics.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from pymongo import MongoClient

SCREEN = "nessunodalnulla"

client = MongoClient("mongodb://localhost:27017/")
db = client["SnareData"]


def parse_date(s):
    try:
        return parsedate_to_datetime(s).replace(tzinfo=None)
    except Exception:
        return None


def detect_media_type(media_list):
    if not media_list:
        return "text"
    types = {m.get("type") for m in media_list}
    if "video" in types or "animated_gif" in types:
        return "video"
    if "photo" in types:
        return "photo"
    return "text"


TOPICS = {
    "Cybersecurity": ["security", "hack", "vulnerabilit", "cyber", "attacc", "exploit", "malware",
                      "phishing", "breach", "ransom", "0day", "cve", "oauth", "infosec", "botnet",
                      "leak", "trojan", "backdoor", "infostealer", "c2 ", " c2,", "payload"],
    "AI/Tech":        ["ai ", "intelligenza artificiale", "llm", "gpt", "claude", "gemini", "modello",
                       "machine learning", "ml ", " deep learning", "openai", "anthropic", "chatgpt"],
    "Crypto":         ["crypto", "bitcoin", "ethereum", "blockchain", "btc", "defi", "token", "nft"],
    "Politica":       ["politic", "governo", "meloni", "elezioni", "pd ", " ue ", "europa", "stato",
                       "ministr", "parlament", "salvini", "schlein", "putin", "trump", "destra",
                       "sinistra", "fasci", "comuni"],
    "Dev/Coding":     ["codice", "sviluppo", "developer", "software", "python", "javascript", "github",
                       " api", "programm", "linux", "docker", "kubernet", "devops"],
    "Maker/Hardware": ["raspberry", "arduino", "3d print", "stampante 3d", "esp32", "esp8266",
                      "firmware", "iot", "sensor", "gpio"],
    "Famiglia/Personale": ["figli", "moglie", "papà", "mamma", "scuola", "famiglia", "casa ", "figlia", "figlio"],
    "Opinioni/Società": ["italia", "italiani", "società", "gente", "paese", "lavoro", "stipendi",
                          "tasse", "giovani", "ricchi", "poveri"],
    "Calcio/Sport":      ["calcio", "juve", "inter", "milan", "napoli", "roma", "lazio", "serie a",
                            "champions", "mondiali", "europei"],
    "Media/Giornalismo": ["giornalist", "stampa", "tg", "rai", "mediaset", "repubblica", "corriere"],
}


def extract_topics(text):
    if not text:
        return ["Altro"]
    t = text.lower()
    found = [name for name, kws in TOPICS.items() if any(k in t for k in kws)]
    return found or ["Altro"]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. USER PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
sample = db.twitter.find_one({"data.data.core.user_results.result.core.screen_name": SCREEN})
u = sample["data"]["data"]["core"]["user_results"]["result"]
profile = {
    "screen_name": SCREEN,
    "name": u.get("core", {}).get("name"),
    "description": u.get("legacy", {}).get("description", ""),
    "followers": u.get("legacy", {}).get("followers_count", 0),
    "following": u.get("legacy", {}).get("friends_count", 0),
    "statuses_count": u.get("legacy", {}).get("statuses_count", 0),
    "account_created": u.get("core", {}).get("created_at"),
    "verified": bool(u.get("verification", {}).get("verified_type")) or bool(u.get("legacy", {}).get("verified")),
    "verified_type": u.get("verification", {}).get("verified_type"),
    "location": u.get("location", {}).get("location"),
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2. ORGANIC POSTS (no RT, no promoted)
# ═══════════════════════════════════════════════════════════════════════════════
pipeline_org = [
    {
        "$match": {
            "data.data.core.user_results.result.core.screen_name": SCREEN,
            "data.data.legacy.retweeted_status_result": {"$exists": False},
            "data.data.legacy.full_text": {"$not": re.compile(r"^RT @")},
            "$or": [
                {"data.data.promoted": {"$exists": False}},
                {"data.data.promoted": False},
                {"data.data.promoted": None},
            ],
        }
    },
    {
        "$project": {
            "tweet_id": "$data.item_id",
            "created_at": "$data.data.legacy.created_at",
            "full_text": "$data.data.legacy.full_text",
            "views": "$data.data.views.count",
            "likes": "$data.data.legacy.favorite_count",
            "retweets": "$data.data.legacy.retweet_count",
            "replies": "$data.data.legacy.reply_count",
            "quotes": "$data.data.legacy.quote_count",
            "bookmarks": "$data.data.legacy.bookmark_count",
            "hashtags": "$data.data.legacy.entities.hashtags",
            "urls": "$data.data.legacy.entities.urls",
            "media": "$data.data.legacy.extended_entities.media",
            "is_quote": "$data.data.legacy.is_quote_status",
            "lang": "$data.data.legacy.lang",
            "in_reply_to": "$data.data.legacy.in_reply_to_screen_name",
        }
    },
]

raw_org = list(db.twitter.aggregate(pipeline_org))
print(f"Organici: {len(raw_org)}")

posts = []
for t in raw_org:
    dt = parse_date(t.get("created_at"))
    if not dt:
        continue
    views = int(t.get("views") or 0)
    likes = int(t.get("likes") or 0)
    rts = int(t.get("retweets") or 0)
    replies = int(t.get("replies") or 0)
    quotes = int(t.get("quotes") or 0)
    bookmarks = int(t.get("bookmarks") or 0)
    engagement = likes + rts + replies + quotes + bookmarks
    er = round(engagement / views * 100, 2) if views > 0 else 0.0
    txt = t.get("full_text") or ""
    tid_raw = t.get("tweet_id")
    tid = str(tid_raw).split(":")[-1] if tid_raw is not None else ""

    posts.append({
        "tweet_id": tid,
        "ts": int(dt.timestamp() * 1000),
        "dt": dt.strftime("%Y-%m-%d"),
        "dt_full": dt.isoformat(),
        "hour": dt.hour,
        "weekday": dt.weekday(),
        "weekday_name": ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"][dt.weekday()],
        "text": txt,
        "len": len(txt),
        "views": views,
        "likes": likes,
        "retweets": rts,
        "replies": replies,
        "quotes": quotes,
        "bookmarks": bookmarks,
        "engagement": engagement,
        "engagement_rate": er,
        "media_type": detect_media_type(t.get("media")),
        "is_reply": bool(t.get("in_reply_to")),
        "has_url": bool(t.get("urls")),
        "hashtags": [h.get("text") for h in (t.get("hashtags") or [])],
        "topics": extract_topics(txt),
        "post_url": f"https://twitter.com/{SCREEN}/status/{tid}" if tid else None,
    })

posts.sort(key=lambda x: x["ts"])

# ═══════════════════════════════════════════════════════════════════════════════
# 3. KPI ORGANICI
# ═══════════════════════════════════════════════════════════════════════════════
views_all = [p["views"] for p in posts]
views_nz = [v for v in views_all if v > 0]
total_views = sum(views_all)
median_views = sorted(views_nz)[len(views_nz)//2] if views_nz else 0
avg_views = round(total_views / len(posts)) if posts else 0
total_engagement = sum(p["engagement"] for p in posts)
avg_er = round(sum(p["engagement_rate"] for p in posts) / len(posts), 2) if posts else 0
top_post = max(posts, key=lambda x: x["views"]) if posts else {}
zero_views = sum(1 for p in posts if p["views"] == 0)
zero_likes = sum(1 for p in posts if p["likes"] == 0)
reply_share = round(sum(1 for p in posts if p["is_reply"]) / len(posts) * 100, 1) if posts else 0
url_share = round(sum(1 for p in posts if p["has_url"]) / len(posts) * 100, 1) if posts else 0

kpis = {
    "total_posts": len(posts),
    "total_views": total_views,
    "median_views": median_views,
    "avg_views": avg_views,
    "total_engagement": total_engagement,
    "avg_engagement_rate": avg_er,
    "top_post_views": top_post.get("views", 0),
    "zero_views_count": zero_views,
    "zero_views_pct": round(zero_views / len(posts) * 100, 1) if posts else 0,
    "zero_likes_count": zero_likes,
    "zero_likes_pct": round(zero_likes / len(posts) * 100, 1) if posts else 0,
    "reply_share_pct": reply_share,
    "url_share_pct": url_share,
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4. MONTHLY / WEEKDAY / HOUR / MEDIA / TOPIC
# ═══════════════════════════════════════════════════════════════════════════════
monthly = defaultdict(lambda: {"posts": 0, "views": 0, "engagement": 0})
for p in posts:
    k = p["dt"][:7]
    monthly[k]["posts"] += 1
    monthly[k]["views"] += p["views"]
    monthly[k]["engagement"] += p["engagement"]
monthly_list = [{"month": k, **v, "avg_views": round(v["views"]/v["posts"]) if v["posts"] else 0}
                for k, v in sorted(monthly.items())]

wd_data = defaultdict(lambda: {"posts": 0, "views": 0, "engagement": 0})
for p in posts:
    wd_data[p["weekday_name"]]["posts"] += 1
    wd_data[p["weekday_name"]]["views"] += p["views"]
    wd_data[p["weekday_name"]]["engagement"] += p["engagement"]
order = ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"]
weekday_list = [{"day": d, "posts": wd_data[d]["posts"],
                 "avg_views": round(wd_data[d]["views"]/wd_data[d]["posts"]) if wd_data[d]["posts"] else 0,
                 "avg_eng": round(wd_data[d]["engagement"]/wd_data[d]["posts"],1) if wd_data[d]["posts"] else 0}
                for d in order]

hr_data = defaultdict(lambda: {"posts": 0, "views": 0, "engagement": 0})
for p in posts:
    hr_data[p["hour"]]["posts"] += 1
    hr_data[p["hour"]]["views"] += p["views"]
    hr_data[p["hour"]]["engagement"] += p["engagement"]
hour_list = [{"hour": h, "posts": hr_data[h]["posts"],
              "avg_views": round(hr_data[h]["views"]/hr_data[h]["posts"]) if hr_data[h]["posts"] else 0,
              "avg_eng": round(hr_data[h]["engagement"]/hr_data[h]["posts"],1) if hr_data[h]["posts"] else 0}
             for h in range(24)]

mt_data = defaultdict(lambda: {"posts": 0, "views": 0, "engagement": 0})
for p in posts:
    mt_data[p["media_type"]]["posts"] += 1
    mt_data[p["media_type"]]["views"] += p["views"]
    mt_data[p["media_type"]]["engagement"] += p["engagement"]
media_list = [{"type": k, "posts": v["posts"],
               "avg_views": round(v["views"]/v["posts"]) if v["posts"] else 0,
               "avg_eng": round(v["engagement"]/v["posts"],1) if v["posts"] else 0}
              for k, v in sorted(mt_data.items(), key=lambda x: -x[1]["views"])]

tp_data = defaultdict(lambda: {"posts": 0, "views": 0, "engagement": 0})
for p in posts:
    for t in p["topics"]:
        tp_data[t]["posts"] += 1
        tp_data[t]["views"] += p["views"]
        tp_data[t]["engagement"] += p["engagement"]
topic_list = [{"topic": k, "posts": v["posts"],
               "avg_views": round(v["views"]/v["posts"]) if v["posts"] else 0,
               "avg_eng": round(v["engagement"]/v["posts"],1) if v["posts"] else 0}
              for k, v in sorted(tp_data.items(), key=lambda x: -x[1]["views"])]

# ═══════════════════════════════════════════════════════════════════════════════
# 5. HASHTAGS
# ═══════════════════════════════════════════════════════════════════════════════
hashtag_counter = Counter()
hashtag_views = defaultdict(int)
for p in posts:
    for h in p["hashtags"]:
        hashtag_counter[h.lower()] += 1
        hashtag_views[h.lower()] += p["views"]
hashtags_list = [{"tag": h, "count": c, "avg_views": round(hashtag_views[h]/c)}
                 for h, c in hashtag_counter.most_common(15)]

# ═══════════════════════════════════════════════════════════════════════════════
# 6. TOP / FLOP POSTS
# ═══════════════════════════════════════════════════════════════════════════════
top20 = sorted(posts, key=lambda x: -x["views"])[:20]
flop = [p for p in posts if p["engagement"] == 0 and len(p["text"]) > 40]
flop_sorted = sorted(flop, key=lambda x: x["ts"], reverse=True)[:10]

# ═══════════════════════════════════════════════════════════════════════════════
# 7. RETWEET ANALYSIS → interessi
# ═══════════════════════════════════════════════════════════════════════════════
pipeline_rt = [
    {"$match": {
        "data.data.core.user_results.result.core.screen_name": SCREEN,
        "data.data.legacy.retweeted_status_result": {"$exists": True},
    }},
    {"$project": {
        "created_at": "$data.data.legacy.created_at",
        "rt_author": "$data.data.legacy.retweeted_status_result.result.core.user_results.result.core.screen_name",
        "rt_author_name": "$data.data.legacy.retweeted_status_result.result.core.user_results.result.core.name",
        "rt_text": "$data.data.legacy.retweeted_status_result.result.legacy.full_text",
        "rt_views": "$data.data.legacy.retweeted_status_result.result.views.count",
        "rt_likes": "$data.data.legacy.retweeted_status_result.result.legacy.favorite_count",
        "rt_hashtags": "$data.data.legacy.retweeted_status_result.result.legacy.entities.hashtags",
    }},
]

raw_rt = list(db.twitter.aggregate(pipeline_rt))
print(f"RT: {len(raw_rt)}")

rt_author_counter = Counter()
rt_author_names = {}
rt_topic_counter = Counter()
rt_hours = Counter()
rt_hashtags = Counter()

rt_items = []
for t in raw_rt:
    a = t.get("rt_author") or "unknown"
    an = t.get("rt_author_name") or a
    rt_author_counter[a] += 1
    rt_author_names[a] = an
    txt = t.get("rt_text") or ""
    for tp in extract_topics(txt):
        rt_topic_counter[tp] += 1
    dt = parse_date(t.get("created_at"))
    if dt:
        rt_hours[dt.hour] += 1
    for h in (t.get("rt_hashtags") or []):
        rt_hashtags[h.get("text", "").lower()] += 1
    rt_items.append({
        "author": a,
        "author_name": an,
        "text": txt[:200],
        "views": int(t.get("rt_views") or 0),
        "likes": int(t.get("rt_likes") or 0),
    })

top_rt_authors = [{"author": a, "name": rt_author_names[a], "count": c}
                  for a, c in rt_author_counter.most_common(15)]
top_rt_topics = [{"topic": t, "count": c} for t, c in rt_topic_counter.most_common()]
top_rt_hashtags = [{"tag": h, "count": c} for h, c in rt_hashtags.most_common(10) if h]

# ═══════════════════════════════════════════════════════════════════════════════
# 8. GROWTH DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════
best_hours = sorted([h for h in hour_list if h["posts"] >= 3], key=lambda x: -x["avg_views"])[:3]
worst_hours = sorted([h for h in hour_list if h["posts"] >= 3], key=lambda x: x["avg_views"])[:3]
best_days = sorted([d for d in weekday_list if d["posts"] > 0], key=lambda x: -x["avg_views"])[:2]

best_media = max(media_list, key=lambda x: x["avg_views"]) if media_list else None
text_media = next((m for m in media_list if m["type"] == "text"), None)

rt_total = len(raw_rt)
org_total = len(posts)
rt_ratio = round(rt_total / (rt_total + org_total) * 100, 1) if (rt_total + org_total) else 0

topic_top = topic_list[0] if topic_list else None
topic_coverage = round(topic_top["posts"] / len(posts) * 100, 1) if topic_top and posts else 0

diagnostics = {
    "best_hours": best_hours,
    "worst_hours": worst_hours,
    "best_days": best_days,
    "best_media": best_media,
    "text_media": text_media,
    "rt_ratio": rt_ratio,
    "rt_total": rt_total,
    "org_total": org_total,
    "topic_top": topic_top,
    "topic_coverage": topic_coverage,
    "zero_views_pct": kpis["zero_views_pct"],
    "zero_likes_pct": kpis["zero_likes_pct"],
    "reply_share_pct": reply_share,
    "url_share_pct": url_share,
    "followers": profile["followers"],
    "median_views": median_views,
    "views_vs_followers_pct": round(median_views / profile["followers"] * 100, 1) if profile["followers"] else 0,
}

# ═══════════════════════════════════════════════════════════════════════════════
# 9. EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
output = {
    "profile": profile,
    "kpis": kpis,
    "posts": posts,
    "monthly": monthly_list,
    "weekday": weekday_list,
    "hours": hour_list,
    "media": media_list,
    "topics": topic_list,
    "hashtags": hashtags_list,
    "top20": top20,
    "flop": flop_sorted,
    "rt": {
        "total": rt_total,
        "top_authors": top_rt_authors,
        "top_topics": top_rt_topics,
        "top_hashtags": top_rt_hashtags,
        "items_sample": rt_items[:50],
    },
    "diagnostics": diagnostics,
    "global_median": median_views,
}

out_path = "/Users/pinperepette/Porgetti/tool-idea/nessunodalnulla-postmortem/nessunodalnulla_data.json"
with open(out_path, "w") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n=== SUMMARY ===")
print(f"Profile: {profile['name']} (@{profile['screen_name']}) — {profile['followers']:,} follower")
print(f"Organici: {len(posts)} | Views totali: {total_views:,} | Mediana: {median_views:,}")
print(f"Zero views: {kpis['zero_views_count']} ({kpis['zero_views_pct']}%)")
print(f"Zero likes: {kpis['zero_likes_count']} ({kpis['zero_likes_pct']}%)")
print(f"Reply share: {reply_share}%")
print(f"RT: {rt_total} — top author: {top_rt_authors[0]['author'] if top_rt_authors else '-'}")
print(f"Top topic RT: {top_rt_topics[0]['topic'] if top_rt_topics else '-'}")
print(f"Top post: {top_post.get('views',0):,} views — {top_post.get('text','')[:80]}")
print(f"\nSalvato: {out_path}")

# Stampa trend mensile per leggere subito il calo
print("\n=== TREND MENSILE (avg_views) ===")
for m in monthly_list:
    print(f"  {m['month']}  posts={m['posts']:>3}  views={m['views']:>8,}  avg={m['avg_views']:>6,}")
