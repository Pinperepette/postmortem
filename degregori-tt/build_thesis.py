#!/usr/bin/env python3
# Merge base dataset + thesis_extra, recompute corpus, add coercion/freedom lexicon + axis.
import json, re, unicodedata
BASE="/Users/pinperepette/Github/postmortem/degregori-tt/"

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)

ds = load(BASE+"dataset.json")
extra = load(BASE+"thesis_extra.json")
stats = load(BASE+"stats.json")

# index by id, merge (extra adds new ids / axis labels)
by_id = {t["id"]: t for t in ds}
for t in extra:
    if t["id"] in by_id:
        by_id[t["id"]]["axis"] = t.get("axis")
    else:
        t.setdefault("engagement", t.get("likes",0)+t.get("retweets",0)+t.get("replies",0)+t.get("quotes",0))
        t.setdefault("sentiment","neutral"); t.setdefault("in_window",True); t.setdefault("hashtags",[])
        by_id[t["id"]] = t
merged = list(by_id.values())

def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))

# ---- Lexicon (substring counts over merged on-topic corpus): n. tweet containing term ----
COERCION = {
    "complice / complicità":[r"compli[cd]"],
    "ignavia":[r"ignav"],
    "deve / serve schierarsi":[r"deve schierar", r"serve schierar", r"bisogna schierar", r"dovere.*schier", r"schierarsi e un dovere", r"schierarsi serve"],
    "vigliacco / codardo / vile":[r"vigliacc", r"codard", r"\bvile\b", r"pavid"],
    "vergogna":[r"vergogn"],
    "fascista (accusa)":[r"fascist"],
    "silenzio (accusa)":[r"silenzio"],
    "emarginare / gulag / rieducare":[r"emargin", r"lebbros", r"gulag", r"rieducar", r"colpirne uno"],
}
FREEDOM = {
    "pensiero unico":[r"pensiero unico"],
    "libero pensiero / libertà":[r"libero pensiero", r"liberta", r"libero arbitrio", r"libero di"],
    "conformismo":[r"conformism"],
    "omologati / pecoroni":[r"omologat", r"pecoron", r"pecora", r"gregge"],
    "dissenso / dissentire":[r"dissens", r"dissentire", r"opinioni difform", r"pensa diversa", r"visione diversa", r"idee tue"],
    "strumentalizzare":[r"strumentaliz"],
    "Orwell / Stasi / Stalin / totalitario":[r"orwell", r"stasi", r"stalin", r"totalitar", r"regime", r"diktat", r"dittatura"],
    "intolleranza / non si accetta":[r"intolleran", r"non accetta", r"non ammess", r"non.*tollerat"],
}
def lex_counts(groups):
    out=[]
    for label, pats in groups.items():
        c=0
        for t in merged:
            tx=norm(t.get("text",""))
            if any(re.search(p, tx) for p in pats): c+=1
        out.append([label,c])
    return sorted(out, key=lambda x:-x[1])

coercion_lex = lex_counts(COERCION)
freedom_lex  = lex_counts(FREEDOM)

# ---- Axis split: use explicit axis, else keyword fallback ----
def classify_axis(t):
    if t.get("axis") in ("coercion","freedom","neutral"): return t["axis"]
    tx=norm(t.get("text",""))
    free_kw=["pensiero unico","libero pensiero","conformism","omologat","strumentaliz","orwell","stasi","stalin","totalitar","non accetta","intolleran","gulag","liberta di"]
    coer_kw=["ignav","compli","deve schierar","serve schierar","bisogna schierar","vigliacc","codard","\bvile\b","silenzio e complic","chi tace","schierarsi e un dovere","schierarsi serve"]
    if any(k in tx for k in free_kw): return "freedom"
    if any(re.search(k,tx) for k in coer_kw): return "coercion"
    return "neutral"

for t in merged: t["_axis"]=classify_axis(t)
axis={"coercion":0,"freedom":0,"neutral":0}
for t in merged: axis[t["_axis"]]+=1
# subset that is thesis-relevant (non-neutral)
thesis_n = axis["coercion"]+axis["freedom"]

# ---- refresh corpus totals ----
n=len(merged)
sum_likes=sum(t.get("likes",0) for t in merged)
sum_views=sum((t.get("views") or 0) for t in merged)
sum_reply=sum(t.get("replies",0) for t in merged)

stats["thesis"]={
  "merged_tweets": n,
  "added_vs_v1": n-len(ds),
  "sum_likes": sum_likes,
  "sum_views": sum_views,
  "sum_replies": sum_reply,
  "axis": axis,
  "axis_pct": {k: round(v*100.0/n,1) for k,v in axis.items()},
  "thesis_relevant": thesis_n,
  "thesis_relevant_pct": round(thesis_n*100.0/n,1),
  "coercion_lexicon": coercion_lex,
  "freedom_lexicon": freedom_lex,
}

with open(BASE+"stats.json","w",encoding="utf-8") as f:
    json.dump(stats,f,ensure_ascii=False,indent=2)
with open(BASE+"dataset.json","w",encoding="utf-8") as f:
    json.dump(merged,f,ensure_ascii=False,indent=2)

print("merged tweets:", n, "(+%d new)"%(n-len(ds)))
print("axis:", axis, "pct", stats["thesis"]["axis_pct"])
print("thesis-relevant:", thesis_n, stats["thesis"]["thesis_relevant_pct"],"%")
print("COERCION lexicon:", coercion_lex)
print("FREEDOM lexicon:", freedom_lex)
print("sum_likes",sum_likes,"sum_views",sum_views,"sum_replies",sum_reply)
