#!/usr/bin/env python3
import json, re, statistics
from collections import defaultdict, Counter

FILES = [
    "/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/mcp-snare-x-tw_search-1780304568115.txt",
    "/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/mcp-snare-x-tw_search-1780305963437.txt",
    "/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/toolu_01HoGZBUA2VtzxRYEWmxEFEk.json",
    "/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/toolu_0136uyMEUAydFhKetnT3JNmp.json",
    "/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/toolu_01RuxRzVNsrb21wZVhirijkN.json",
]

def load_obj(raw):
    raw = raw.strip()
    try:
        v = json.loads(raw)
    except Exception:
        # raw_decode from first {
        i = raw.find("{")
        v, _ = json.JSONDecoder().raw_decode(raw[i:])
        return v
    # v could be list with [0]['text']
    if isinstance(v, list) and v and isinstance(v[0], dict) and "text" in v[0]:
        return json.loads(v[0]["text"])
    if isinstance(v, dict) and "tweets" in v:
        return v
    if isinstance(v, dict):
        return v
    raise ValueError("unrecognized")

def to_int(x):
    try:
        return int(x or 0)
    except Exception:
        return 0

# Collect candidate rows
candidates = []
for f in FILES:
    with open(f, encoding="utf-8") as fh:
        raw = fh.read()
    obj = load_obj(raw)
    tweets = obj.get("tweets", []) if isinstance(obj, dict) else []
    for t in tweets:
        candidates.append((t, False))
        qt = t.get("quoted_tweet")
        if qt:
            candidates.append((qt, True))

raw_rows = len(candidates)

# Dedup by id keep highest likes; track if ever seen as non-quote (original)
best = {}
seen_as_original = set()
for t, is_quote_only in candidates:
    tid = t.get("id")
    if tid is None:
        continue
    likes = to_int(t.get("metrics", {}).get("likes"))
    if not is_quote_only:
        seen_as_original.add(tid)
    if tid not in best or likes > best[tid][1]:
        best[tid] = (t, likes)

NEWS = {"repubblica","lastampa","corriere","corriereit","adnkronos","ilfattoquotidiano",
        "secoloditalia","libero","liberoquotidiano","fattoquotidiano"}

PRO_MARK = ["ha ragione","grande de gregori","artista libero","pensiero unico","lasciatelo in pace",
            "chapeau","coraggio","non si inginocchia","d'accordo con de gregori","sto con de gregori",
            "viva de gregori","bravo de gregori","ben detto","santo subito","applausi","quanto ha ragione",
            "che signore","libertà","libero di"]
ANTI_MARK = ["ignavia","complicità","complicita","codardo","vergogna","figura di merda","che pena",
             "si faccia i cazzi suoi","deve schierarsi","serve schierarsi","non sono d'accordo con de gregori",
             "buffone","menestrello","schifo","patetico","ipocrita","ipocrisia","deludente","delusione",
             "vigliacco","squallido","triste"]

def classify(text, handle, date_iso):
    tl = (text or "").lower()
    h = (handle or "").lower()
    # offtopic by date
    if not date_iso or date_iso < "2026-05-25":
        return "offtopic"
    # must mention de gregori or clearly the controversy
    mentions = "de gregori" in tl or "degregori" in tl or "@fdegregori" in tl
    # anti markers
    anti = any(m in tl for m in ANTI_MARK)
    pro = any(m in tl for m in PRO_MARK)
    # favorable contrasts (someone else as good example) => anti de gregori
    if "iacchetti" in tl or "springsteen" in tl:
        anti = True
    if "genocidio" in tl and mentions:
        # critical context
        anti = anti or True if not pro else anti
    if h in NEWS:
        if pro and not anti:
            return "pro"
        if anti and not pro:
            return "anti"
        return "neutral"
    if pro and not anti:
        return "pro"
    if anti and not pro:
        return "anti"
    if pro and anti:
        # tie-break: count
        return "anti"
    if not mentions:
        return "neutral"
    return "neutral"

def media_type(t):
    media = t.get("media") or []
    if media and isinstance(media, list):
        mt = media[0].get("type")
        if mt in ("video","photo"):
            return mt
        if mt == "animated_gif":
            return "video"
    return "text"

HASH_RE = re.compile(r"#\w+")

rows = []
for tid,(t,_lk) in best.items():
    m = t.get("metrics", {}) or {}
    a = t.get("author", {}) or {}
    text = t.get("text") or ""
    date_iso = t.get("created_at") or ""
    handle = a.get("handle") or ""
    likes = to_int(m.get("likes")); rts = to_int(m.get("retweets"))
    replies = to_int(m.get("replies")); quotes = to_int(m.get("quotes"))
    views = to_int(m.get("views")); bms = to_int(m.get("bookmarks"))
    sent = classify(text, handle, date_iso)
    in_window = bool(date_iso) and date_iso >= "2026-05-26"
    if not in_window:
        sent = "offtopic"
    rows.append({
        "id": tid,
        "url": t.get("url") or "",
        "handle": handle,
        "name": a.get("name") or "",
        "verified": bool(a.get("verified")),
        "followers": to_int(a.get("followers")),
        "date": date_iso,
        "text": text,
        "likes": likes, "retweets": rts, "replies": replies, "quotes": quotes,
        "views": views, "bookmarks": bms,
        "media_type": media_type(t),
        "is_quote": tid not in seen_as_original,
        "hashtags": [h.lower() for h in HASH_RE.findall(text)],
        "engagement": likes+rts+replies+quotes,
        "sentiment": sent,
        "in_window": in_window,
    })

unique_tweets = len(rows)
ontopic = [r for r in rows if r["in_window"] and r["sentiment"] != "offtopic"]
offtopic = [r for r in rows if not (r["in_window"] and r["sentiment"] != "offtopic")]

dates = [r["date"] for r in rows if r["date"]]
date_min = min(dates) if dates else None
date_max = max(dates) if dates else None

def s(rs, k): return sum(r[k] for r in rs)

engs = [r["engagement"] for r in ontopic]
kpis = {
    "tweets": len(ontopic),
    "sum_likes": s(ontopic,"likes"),
    "sum_rt": s(ontopic,"retweets"),
    "sum_replies": s(ontopic,"replies"),
    "sum_quotes": s(ontopic,"quotes"),
    "sum_views": s(ontopic,"views"),
    "sum_bookmarks": s(ontopic,"bookmarks"),
    "sum_engagement": s(ontopic,"engagement"),
    "avg_engagement": round(statistics.mean(engs),2) if engs else 0,
    "median_engagement": statistics.median(engs) if engs else 0,
    "verified_count": sum(1 for r in ontopic if r["verified"]),
    "verified_pct": round(100*sum(1 for r in ontopic if r["verified"])/len(ontopic),1) if ontopic else 0,
    "video_count": sum(1 for r in ontopic if r["media_type"]=="video"),
    "video_pct": round(100*sum(1 for r in ontopic if r["media_type"]=="video")/len(ontopic),1) if ontopic else 0,
}

# timeline daily
daily = defaultdict(lambda: {"count":0,"likes":0,"views":0,"engagement":0})
for r in ontopic:
    d = r["date"][:10]
    daily[d]["count"]+=1; daily[d]["likes"]+=r["likes"]
    daily[d]["views"]+=r["views"]; daily[d]["engagement"]+=r["engagement"]
timeline_daily = [{"date":d, **v} for d,v in sorted(daily.items())]

# hourly UTC
hourly = [0]*24
for r in ontopic:
    m = re.search(r"T(\d{2}):", r["date"])
    if m:
        hourly[int(m.group(1))]+=1

sentiment = {"pro":0,"anti":0,"neutral":0,"offtopic":0}
for r in rows:
    if r in ontopic:
        sentiment[r["sentiment"]] = sentiment.get(r["sentiment"],0)+1
    else:
        sentiment["offtopic"]+=1
sentiment_engagement = {"pro":0,"anti":0,"neutral":0}
for r in ontopic:
    sentiment_engagement[r["sentiment"]] += r["likes"]
n_ot = len(ontopic) or 1
sentiment_pct = {k: round(100*sentiment.get(k,0)/n_ot,1) for k in ("pro","anti","neutral")}

# authors
auth = defaultdict(lambda: {"handle":"","name":"","verified":False,"followers":0,"tweets":0,"sum_engagement":0,"sum_likes":0})
for r in ontopic:
    a = auth[r["handle"]]
    a["handle"]=r["handle"]; a["name"]=r["name"]; a["verified"]=r["verified"]
    a["followers"]=max(a["followers"],r["followers"])
    a["tweets"]+=1; a["sum_engagement"]+=r["engagement"]; a["sum_likes"]+=r["likes"]
authors = list(auth.values())
top_authors_by_count = sorted(authors, key=lambda x:(-x["tweets"],-x["sum_engagement"]))[:15]
top_authors_by_engagement = sorted(authors, key=lambda x:-x["sum_engagement"])[:15]

top_tweets = sorted(ontopic, key=lambda r:-r["likes"])[:25]
top_tweets_out = [{k:r[k] for k in ("id","url","handle","name","verified","date","text","likes","retweets","replies","quotes","views","media_type","sentiment")} for r in top_tweets]

hc = Counter()
for r in ontopic:
    hc.update(r["hashtags"])
hashtags = [{"tag":t,"count":c} for t,c in hc.most_common(20)]

ENT_KEYS = ["springsteen","iacchetti","elisa","ruggeri","vasco","guccini","castaldo","berizzi",
            "roger waters","gaza","palestina","flotilla","sanremo","tenco","israele","genocidio",
            "pensiero unico","ignavia"]
entities = {k:0 for k in ENT_KEYS}
for r in ontopic:
    tl = r["text"].lower()
    for k in ENT_KEYS:
        if k in tl:
            entities[k]+=1

media_split = {"text":0,"photo":0,"video":0}
for r in ontopic:
    media_split[r["media_type"]] = media_split.get(r["media_type"],0)+1

def lbucket(l):
    if l==0: return "0"
    if l<10: return "1-9"
    if l<100: return "10-99"
    if l<1000: return "100-999"
    return "1000+"
engagement_buckets = {"0":0,"1-9":0,"10-99":0,"100-999":0,"1000+":0}
for r in ontopic:
    engagement_buckets[lbucket(r["likes"])]+=1

def fbucket(f):
    if f<1000: return "<1k"
    if f<10000: return "1k-10k"
    if f<100000: return "10k-100k"
    return "100k+"
followers_buckets = {"<1k":0,"1k-10k":0,"10k-100k":0,"100k+":0}
for a in authors:
    followers_buckets[fbucket(a["followers"])]+=1

quote_vs_original = {"original":sum(1 for r in ontopic if not r["is_quote"]),
                     "quote":sum(1 for r in ontopic if r["is_quote"])}

stats = {
    "corpus": {
        "raw_rows": raw_rows,
        "unique_tweets": unique_tweets,
        "ontopic_tweets": len(ontopic),
        "offtopic_tweets": len(offtopic),
        "date_min": date_min,
        "date_max": date_max,
        "queries_used": 6,
    },
    "kpis": kpis,
    "timeline_daily": timeline_daily,
    "timeline_hourly": hourly,
    "sentiment": sentiment,
    "sentiment_engagement": sentiment_engagement,
    "sentiment_pct": sentiment_pct,
    "top_authors_by_count": top_authors_by_count,
    "top_authors_by_engagement": top_authors_by_engagement,
    "top_tweets": top_tweets_out,
    "hashtags": hashtags,
    "entities": entities,
    "media_split": media_split,
    "engagement_buckets": engagement_buckets,
    "followers_buckets": followers_buckets,
    "quote_vs_original": quote_vs_original,
}

with open("/Users/pinperepette/Github/postmortem/degregori-tt/dataset.json","w",encoding="utf-8") as f:
    json.dump(ontopic, f, ensure_ascii=False, indent=2)
with open("/Users/pinperepette/Github/postmortem/degregori-tt/stats.json","w",encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

# headline summary
print("RAW_ROWS", raw_rows)
print("UNIQUE", unique_tweets)
print("ONTOPIC", len(ontopic))
print("DATE", date_min, "->", date_max)
print("SUM_LIKES", kpis["sum_likes"], "SUM_VIEWS", kpis["sum_views"])
print("SENTIMENT", sentiment, "PCT", sentiment_pct)
print("TOP5_TWEETS")
for r in top_tweets[:5]:
    print("  ", r["handle"], r["likes"])
print("TOP5_AUTHORS_ENG")
for a in top_authors_by_engagement[:5]:
    print("  ", a["handle"], a["sum_engagement"])
print("TOP8_HASHTAGS", hashtags[:8])
