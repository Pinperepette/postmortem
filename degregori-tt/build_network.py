#!/usr/bin/env python3
# Build interaction graph + per-axis wordclouds + viral phrases + litigiosità index.
import json, re, unicodedata
from collections import defaultdict, Counter
BASE="/Users/pinperepette/Github/postmortem/degregori-tt/"
TR="/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/"
RAW=["mcp-snare-x-tw_search-1780304568115.txt","mcp-snare-x-tw_search-1780305963437.txt",
     "toolu_01HoGZBUA2VtzxRYEWmxEFEk.json","toolu_0136uyMEUAydFhKetnT3JNmp.json","toolu_01RuxRzVNsrb21wZVhirijkN.json"]

def inner(raw):
    try:
        o=json.loads(raw)
        if isinstance(o,list) and o and isinstance(o[0],dict) and 'text' in o[0]: return json.loads(o[0]['text'])
        if isinstance(o,dict) and 'tweets' in o: return o
    except: pass
    s=raw.find('{'); return json.JSONDecoder().raw_decode(raw[s:])[0]

raw_tweets=[]
for fn in RAW:
    try: txt=open(TR+fn,encoding="utf-8").read()
    except: continue
    for t in inner(txt).get('tweets',[]):
        raw_tweets.append(t)
        if t.get('quoted_tweet'): raw_tweets.append(t['quoted_tweet'])

# --- stance per handle from dataset.json (merged 235) ---
ds=json.load(open(BASE+"dataset.json",encoding="utf-8"))
hd_sent=defaultdict(list)
for t in ds: hd_sent[t["handle"].lower()].append(t.get("sentiment","neutral"))
def stance_of(h):
    s=hd_sent.get(h.lower())
    if not s: return "neutral"
    c=Counter(s); pro=c.get("pro",0); con=c.get("contro",0)
    if pro>con: return "pro"
    if con>pro: return "contro"
    return "neutral"

MENT=re.compile(r'@(\w+)')
eng=defaultdict(int); seen=set(); edges=Counter()
for t in raw_tweets:
    a=t.get('author') or {}
    h=a.get('handle')
    if not h or t.get('id') in seen: continue
    seen.add(t.get('id'))
    m=t.get('metrics',{})
    e=m.get('likes',0)+m.get('retweets',0)+m.get('replies',0)+m.get('quotes',0)
    eng[h]+=e
    rt=t.get('reply_to_handle')
    if rt and rt!=h: edges[(h,rt,'reply')]+=1
    qt=t.get('quoted_tweet')
    if qt and (qt.get('author') or {}).get('handle'):
        qh=qt['author']['handle']
        if qh!=h: edges[(h,qh,'quote')]+=1
    for mh in MENT.findall(t.get('text','') or ''):
        if mh!=h and mh!=rt: edges[(h,mh,'mention')]+=1

indeg=defaultdict(int); outdeg=defaultdict(int)
for (s,d,ty),w in edges.items(): indeg[d]+=w; outdeg[s]+=w
allh=set(eng)|set(indeg)|set(outdeg)
# keep significant nodes
def keep(h): return eng.get(h,0)>=15 or indeg.get(h,0)>=2 or (outdeg.get(h,0)+indeg.get(h,0))>=3
cand=set(h for h in allh if keep(h))
links0=[(s,d,ty,w) for (s,d,ty),w in edges.items() if s in cand and d in cand]
connected=set()
for s,d,ty,w in links0: connected.add(s); connected.add(d)
top_eng=set(sorted(cand,key=lambda h:-eng.get(h,0))[:18])
nh=connected|top_eng
nodes=[{"id":h,"eng":eng.get(h,0),"indeg":indeg.get(h,0),"outdeg":outdeg.get(h,0),"stance":stance_of(h)} for h in nh]
nodes.sort(key=lambda x:-(x["eng"]+x["indeg"]*30))
links=[{"s":s,"t":d,"type":ty,"w":w} for (s,d,ty,w) in links0 if s in nh and d in nh]

# --- wordclouds per axis ---
STOP=set("di a da in con su per tra fra il lo la i gli le un uno una e ma o che chi cui non è e' sono ha ho hai abbiamo anche come piu meno se si sì no ci vi mi ti ne del della dei delle degli al allo alla ai agli alle dal dalla dallo nei nel nella sul sulla questo questa quello quella quel suo sua sue suoi loro lui lei noi voi io tu perche perché quando dove cosa fa fare essere stato stata molto tutto tutti tutte gia già ancora solo poi qui la là ora mai sempre quindi cosi così pure ovvero proprio sé se stesso ogni qualche tanto cioè dire detto dice fatto verso senza sotto sopra contro dopo prima me te lui sia siamo siete erano era avere aver glie van vuoi vuole deve devono può puo cazzo merda".split())
def toks(txt):
    txt=unicodedata.normalize("NFKD",txt.lower())
    txt="".join(c for c in txt if not unicodedata.combining(c))
    txt=re.sub(r'http\S+','',txt); txt=re.sub(r'[@#]\w+','',txt)
    words=re.findall(r"[a-zàèéìòù']{4,}",txt)
    return [w for w in words if w not in STOP and 'gregori' not in w and w not in ('degregori','francesco','erri','luca')]
axis_of={t["id"]:t.get("axis") for t in ds}
# reload thesis_extra axis too (already merged in ds as 'axis' maybe missing) -> use ds 'axis' or sentiment
def node_axis(t):
    ax=t.get("axis")
    if ax in ("coercion","freedom"): return ax
    s=t.get("sentiment")
    return {"pro":"freedom","contro":"coercion"}.get(s,"neutral")
wc=defaultdict(Counter)
for t in ds:
    ax=node_axis(t)
    if ax in ("freedom","coercion"):
        for w in toks(t.get("text","")): wc[ax][w]+=1
wc_freedom=wc["freedom"].most_common(22)
wc_coercion=wc["coercion"].most_common(22)

# --- viral phrases: count + cumulative likes, with frame ---
PHRASES=[
 ("PRO","pensiero unico",[r"pensiero unico"]),
 ("PRO","libero pensiero / libertà",[r"libero pensiero",r"liberta"]),
 ("PRO","conformismo",[r"conformism"]),
 ("PRO","pecoroni / omologati",[r"omologat",r"pecoron",r"gregge"]),
 ("PRO","artista libero",[r"artista libero",r"uomo libero",r"libero arbitrio"]),
 ("PRO","Orwell / Stasi / totalitario",[r"orwell",r"stasi",r"stalin",r"totalitar"]),
 ("CONTRO","ignavia",[r"ignav"]),
 ("CONTRO","è complicità / complice",[r"compli[cd]"]),
 ("CONTRO","serve / deve schierarsi",[r"serve schierar",r"deve schierar",r"bisogna schierar",r"schierarsi e un dovere",r"schierarsi serve"]),
 ("CONTRO","silenzio",[r"silenzio"]),
 ("CONTRO","vigliacco / codardo / vile",[r"vigliacc",r"codard",r"\bvile\b"]),
 ("CONTRO","Gaza / genocidio",[r"gaza",r"genocid"]),
]
def normt(s):
    s=unicodedata.normalize("NFKD",s.lower()); return "".join(c for c in s if not unicodedata.combining(c))
viral=[]
for frame,label,pats in PHRASES:
    n=0; lk=0
    for t in ds:
        tx=normt(t.get("text",""))
        if any(re.search(p,tx) for p in pats):
            n+=1; lk+=t.get("likes",0)
    viral.append({"frame":frame,"phrase":label,"count":n,"likes":lk})
viral.sort(key=lambda x:-x["likes"])

# --- litigiosità ---
SL=sum(t.get("likes",0) for t in ds); SR=sum(t.get("retweets",0) for t in ds)
SRe=sum(t.get("replies",0) for t in ds); SQ=sum(t.get("quotes",0) for t in ds)
lit={"sum_likes":SL,"sum_rt":SR,"sum_replies":SRe,"sum_quotes":SQ,
     "reply_per_rt":round(SRe/SR,2) if SR else None,
     "reply_per_rt_like":round(SRe/(SR+SL),3) if (SR+SL) else None}

# --- stance counts + engagement + attention battle (excl. media) ---
stance=Counter(t.get("sentiment","neutro") for t in ds)
stance_likes=defaultdict(int)
for t in ds: stance_likes[t.get("sentiment","neutro")]+=t.get("likes",0)
def attrow(key,label):
    tw=[t for t in ds if t.get("sentiment")==key]
    n=len(tw); lk=sum(t.get("likes",0) for t in tw)
    return {"frame":label,"key":key,"n":n,"likes":lk,"per_tweet":round(lk/n,1) if n else 0}
attention=[attrow("pro","Pro De Gregori"),attrow("contro","Contro"),attrow("neutro","Neutro / Meno schierati")]
nonmedia=[t for t in ds if not t.get("is_media")]
schier=[t for t in nonmedia if t.get("sentiment") in ("pro","contro")]
tot_l=sum(t.get("likes",0) for t in ds); tot_n=len(ds)
sl=sum(t.get("likes",0) for t in schier)
attention_takeaway={
  "schierati_n":len(schier),"schierati_pct_tweet":round(len(schier)*100/tot_n,1),
  "schierati_likes":sl,"schierati_pct_likes":round(sl*100/tot_l,1),
  "pro_pct_of_schierati_tweet":round(stance["pro"]*100/(stance["pro"]+stance["contro"]),1),
  "pro_pct_of_schierati_likes":round(stance_likes["pro"]*100/(stance_likes["pro"]+stance_likes["contro"]),1),
}
out={"nodes":nodes,"links":links,"wc_freedom":wc_freedom,"wc_coercion":wc_coercion,
     "viral":viral,"litigiosita":lit,
     "stance":dict(stance),"stance_likes":dict(stance_likes),
     "attention":attention,"attention_takeaway":attention_takeaway,
     "graph_meta":{"n_nodes":len(nodes),"n_links":len(links),"from_raw_tweets":len(seen)}}
json.dump(out,open(BASE+"network.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("nodes",len(nodes),"links",len(links),"raw",len(seen))
print("top nodes by in-degree:",sorted(nodes,key=lambda x:-x["indeg"])[:8] and [(n["id"],n["indeg"],n["stance"]) for n in sorted(nodes,key=lambda x:-x["indeg"])[:8]])
print("litigiosita",lit)
print("viral top:",[(v["frame"],v["phrase"],v["count"],v["likes"]) for v in viral[:6]])
print("wc_freedom",wc_freedom[:10])
print("wc_coercion",wc_coercion[:10])

# ---- benchmark litigiosità on comparison topics (top samples) ----
def load_any(fn):
    txt=open(TR+fn,encoding="utf-8").read()
    return inner(txt).get('tweets',[])
def idx(tws, drop_gregori=False):
    L=R=Re=0; n=0
    for t in tws:
        if drop_gregori and 'gregori' in (t.get('text','') or '').lower(): continue
        m=t.get('metrics',{}); L+=m.get('likes',0); R+=m.get('retweets',0); Re+=m.get('replies',0); n+=1
    return {"n":n,"reply_per_rt":round(Re/R,2) if R else None,"reply_per_rt_like":round(Re/(R+L),3) if (R+L) else None,"likes":L,"rt":R,"replies":Re}
bench={}
try: bench["Sanremo (no DeGregori)"]=idx(load_any("toolu_013gv6GRkfk5d3FTocSeKPp3.json"),drop_gregori=True)
except Exception as e: print("sanremo err",e)
try: bench["Champions"]=idx(load_any("mcp-snare-x-tw_search-1780308147279.txt"))
except Exception as e: print("champ err",e)
try: bench["Meloni"]=idx(load_any("mcp-snare-x-tw_search-1780308170634.txt"))
except Exception as e: print("meloni err",e)
out["benchmark"]=bench
json.dump(out,open(BASE+"network.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("BENCHMARK:")
for k,v in bench.items(): print(" ",k,"reply/RT",v["reply_per_rt"],"reply/(rt+like)",v["reply_per_rt_like"],"n",v["n"])
