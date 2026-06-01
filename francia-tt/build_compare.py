#!/usr/bin/env python3
import json, glob, re
from collections import defaultdict, Counter
BASE="/Users/pinperepette/Github/postmortem/francia-tt/"
TR="/Users/pinperepette/.claude/projects/-Users-pinperepette-Github-postmortem/5a281da5-638d-4f94-9bd6-f51d4fd45ad8/tool-results/"

def load(p): return json.load(open(p,encoding="utf-8"))
fr=load(BASE+"fr_dataset.json"); it=load(BASE+"it_dataset.json")

# ---- avatars from raw files ----
def inner(raw):
    try:
        o=json.loads(raw)
        if isinstance(o,list) and o and isinstance(o[0],dict) and 'text' in o[0]: return json.loads(o[0]['text'])
        if isinstance(o,dict) and 'tweets' in o: return o
    except: pass
    s=raw.find('{'); return json.JSONDecoder().raw_decode(raw[s:])[0]
AV={}
for fn in glob.glob(TR+"*"):
    try: raw=open(fn,encoding="utf-8").read()
    except: continue
    try: obj=inner(raw)
    except: continue
    for t in obj.get('tweets',[]):
        for tw in (t, t.get('quoted_tweet') or {}):
            a=tw.get('author') or {}
            if a.get('handle') and a.get('avatar'): AV.setdefault(a['handle'].lower(),a['avatar'])

def dom(rows): return [t for t in rows if not t.get('foreign')]

def framedist(rows):
    d=defaultdict(lambda:[0,0])
    for t in rows: d[t.get('frame','other')][0]+=1; d[t.get('frame','other')][1]+=t.get('likes',0)
    return {k:{"n":v[0],"likes":v[1]} for k,v in d.items()}

def toptweets(rows,k=12):
    out=[]
    for t in sorted(rows,key=lambda x:-x.get('likes',0))[:k]:
        h=t['handle']
        out.append({"h":h,"n":t.get('name',h),"v":t.get('verified',False),"av":AV.get(h.lower()),
                    "likes":t.get('likes',0),"rt":t.get('retweets',0),"rp":t.get('replies',0),
                    "vw":t.get('views') or 0,"frame":t.get('frame','other'),"date":t.get('date','')[:10],
                    "url":t.get('url',''),"txt":(t.get('text','') or '')[:240]})
    return out

def hashtags(rows,k=12):
    c=Counter()
    for t in rows:
        for h in (t.get('hashtags') or []): c[h.lower()]+=1
    return c.most_common(k)

def actors(rows):
    return dict(Counter(t.get('actor','user') for t in rows))

frd, itd = dom(fr), dom(it)
def pct(rows,frames):
    n=len(rows); lk=sum(t.get('likes',0) for t in rows)
    ni=sum(1 for t in rows if t.get('frame') in frames); li=sum(t.get('likes',0) for t in rows if t.get('frame') in frames)
    return {"n_pct":round(ni*100/n) if n else 0,"like_pct":round(li*100/lk) if lk else 0}

CMP={
 "meta":{
   "fr_ontopic":len(fr),"fr_dom":len(frd),"fr_foreign":sum(1 for t in fr if t.get('foreign')),
   "it_ontopic":len(it),"it_dom":len(itd),"it_foreign":sum(1 for t in it if t.get('foreign')),
   "fr_authors":len({t['handle'].lower() for t in frd}),"it_authors":len({t['handle'].lower() for t in itd}),
   "total":len(fr)+len(it)
 },
 "toll":{"arrests":780,"arrests_paris":480,"injured":219,"police_injured":57,"dead":1,"communes":71,"loot_cities":15},
 "fr":{"frames":framedist(frd),"top":toptweets(frd),"hashtags":hashtags(frd),"actors":actors(frd),
       "imm":pct(frd,{'immigration'}),"hool":pct(frd,{'hooliganism'}),"police":pct(frd,{'police_state'}),"counter":pct(frd,{'counter'})},
 "it":{"frames":framedist(itd),"top":toptweets(itd),"hashtags":hashtags(itd),"actors":actors(itd),
       "imm":pct(itd,{'immigration','italy_link'}),"hool":pct(itd,{'hooliganism'}),"police":pct(itd,{'police_state'}),"counter":pct(itd,{'counter'})},
}
json.dump(CMP,open(BASE+"compare.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
open(BASE+"compare_data.js","w",encoding="utf-8").write("window.CMP="+json.dumps(CMP,ensure_ascii=False)+";")
print("FR dom",len(frd),"IT dom",len(itd),"total on-topic",CMP['meta']['total'])
print("FR frames",{k:v['n'] for k,v in CMP['fr']['frames'].items()})
print("IT frames",{k:v['n'] for k,v in CMP['it']['frames'].items()})
print("imm FR",CMP['fr']['imm'],"imm IT",CMP['it']['imm'])
print("avatars resolved FR top:",sum(1 for t in CMP['fr']['top'] if t['av']),"/12  IT top:",sum(1 for t in CMP['it']['top'] if t['av']),"/12")
