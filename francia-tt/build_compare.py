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

# ---- foreign amplifiers: presence in FR vs IT raw files (incl. quoted) ----
FR_FILES=["mcp-snare-x-tw_search-1780313060786.txt","mcp-snare-x-tw_search-1780313199461.txt","mcp-snare-x-tw_search-1780313267926.txt","mcp-snare-x-tw_search-1780313443138.txt","mcp-snare-x-tw_search-1780313487399.txt","mcp-snare-x-tw_search-1780313935013.txt","mcp-snare-x-tw_search-1780313957223.txt","mcp-snare-x-tw_search-1780313976494.txt"]
IT_FILES=["mcp-snare-x-tw_search-1780313101216.txt","mcp-snare-x-tw_search-1780313303716.txt","mcp-snare-x-tw_search-1780313331967.txt","mcp-snare-x-tw_search-1780313413686.txt","mcp-snare-x-tw_search-1780314004777.txt","toolu_01RbSfr4hKkhZ8avN5cdwciW.json","mcp-snare-x-tw_search-1780314152201.txt"]
def handles_in(files):
    seen=defaultdict(lambda:{"likes":0,"name":None,"av":None})
    for fn in files:
        try: obj=inner(open(TR+fn,encoding="utf-8").read())
        except: continue
        for t in obj.get('tweets',[]):
            for tw in (t, t.get('quoted_tweet') or {}):
                a=tw.get('author') or {}; h=(a.get('handle') or '').lower()
                if not h: continue
                lk=(tw.get('metrics') or {}).get('likes',0) or 0
                if lk>=seen[h]['likes']: seen[h]['likes']=lk; seen[h]['name']=a.get('name'); seen[h]['av']=a.get('avatar')
    return seen
frH=handles_in(FR_FILES); itH=handles_in(IT_FILES)
AMP=['elonmusk','EndWokeness','MarioNawfal','MAGAVoice','AgustinLaje','Liberfach0','danilerer','realMaalouf','TRobinsonNewEra','javiernegre10','F_Desouche']
amps=[]
for h in AMP:
    lk=h.lower(); infr=lk in frH; init=lk in itH
    if not(infr or init): continue
    src=frH.get(lk) or itH.get(lk)
    amps.append({"h":h,"name":src.get('name') or h,"av":src.get('av'),
                 "fr":infr,"it":init,"fr_likes":frH.get(lk,{}).get('likes',0),"it_likes":itH.get(lk,{}).get('likes',0),
                 "max_likes":max(frH.get(lk,{}).get('likes',0),itH.get(lk,{}).get('likes',0))})
amps.sort(key=lambda x:-x['max_likes'])
def effN(frames):  # effective number of frames (1/HHI): higher=more frammentato
    n=sum(f['n'] for f in frames.values());
    if not n: return 0
    return round(1/sum((f['n']/n)**2 for f in frames.values()),2)
def topshare(frames):
    n=sum(f['n'] for f in frames.values());
    return round(max(f['n'] for f in frames.values())*100/n) if n else 0
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
       "imm":pct(itd,{'immigration'}),"hool":pct(itd,{'hooliganism'}),"police":pct(itd,{'police_state'}),"counter":pct(itd,{'counter'})},
}
# fragmentation + consensus delta
frF=CMP['fr']['frames']; itF=CMP['it']['frames']
def npct(frames):
    n=sum(f['n'] for f in frames.values()); return {k:round(v['n']*100/n) for k,v in frames.items()} if n else {}
frpc, itpc = npct(frF), npct(itF)
order=['immigration','hooliganism','police_state','counter','italy_link','antisemitism','news','mockery','other']
consensus=[]
for k in order:
    if k in frpc or k in itpc:
        f=frpc.get(k,0); i=itpc.get(k,0)
        consensus.append({"frame":k,"fr":f,"it":i,"delta":i-f})
CMP['amps']=amps
CMP['frag']={"fr_effN":effN(frF),"it_effN":effN(itF),"fr_top":topshare(frF),"it_top":topshare(itF)}
CMP['consensus']=consensus

# ---- advanced metrics ----
import math
def props(frames):
    n=sum(f['n'] for f in frames.values()); return {k:v['n']/n for k,v in frames.items()} if n else {}
def entropy(frames):
    p=props(frames); return round(-sum(x*math.log2(x) for x in p.values() if x>0),2)
def hhi(frames):
    p=props(frames); return round(sum(x*x for x in p.values()),3)
pf, pi = props(frF), props(itF)
allk=set(pf)|set(pi)
dist=round(0.5*sum(abs(pf.get(k,0)-pi.get(k,0)) for k in allk),2)
def lorenz(frames):
    p=sorted(props(frames).values(),reverse=True)
    cum=[];s=0
    for x in p: s+=x; cum.append(round(s,3))
    xs=[round((i+1)/len(cum),3) for i in range(len(cum))]
    return {"x":[0]+xs,"y":[0]+cum}
# assuefazione index A = gravità(=1, stesso evento) / quota-attenzione-alla-causa(immigrazione)
imm_fr=pf.get('immigration',0.0001); imm_it=pi.get('immigration',0.0001)
CMP['metrics']={
  "entropy_fr":entropy(frF),"entropy_it":entropy(itF),
  "hhi_fr":hhi(frF),"hhi_it":hhi(itF),
  "distance":dist,
  "distance_eucl":round(math.sqrt(sum((pf.get(k,0)-pi.get(k,0))**2 for k in (set(pf)|set(pi)))),2),
  "lorenz_fr":lorenz(frF),"lorenz_it":lorenz(itF),
  "assuef_fr":round(1/imm_fr,1),"assuef_it":round(1/imm_it,1),
  "imm_fr_pct":round(imm_fr*100),"imm_it_pct":round(imm_it*100),
  "gap_fr":CMP['fr']['imm']['like_pct']-CMP['fr']['imm']['n_pct'],
  "gap_it":CMP['it']['imm']['like_pct']-CMP['it']['imm']['n_pct'],
  "fr_imm_tweet":CMP['fr']['imm']['n_pct'],"fr_imm_like":CMP['fr']['imm']['like_pct'],
  "it_imm_tweet":CMP['it']['imm']['n_pct'],"it_imm_like":CMP['it']['imm']['like_pct']
}

# ---- amplifier -> quoter network (from raw) ----
AMPSET={a['h'].lower() for a in amps}
FRFILES=set(FR_FILES);
def filelang(fn): return 'fr' if fn in FRFILES else 'it'
edges=[]; qnodes={}
for fn in FR_FILES+IT_FILES:
    try: obj=inner(open(TR+fn,encoding="utf-8").read())
    except: continue
    for t in obj.get('tweets',[]):
        q=t.get('quoted_tweet')
        if not q: continue
        qa=(q.get('author') or {}).get('handle','').lower()
        if qa in AMPSET:
            quoter=(t.get('author') or {}).get('handle')
            if not quoter: continue
            lang=t.get('lang') or filelang(fn)
            lk=(t.get('metrics') or {}).get('likes',0) or 0
            edges.append({"amp":qa,"q":quoter,"lang":('it' if lang=='it' else 'fr'),"likes":lk})
            k=quoter.lower()
            if k not in qnodes or lk>qnodes[k]['likes']:
                qnodes[k]={"h":quoter,"lang":('it' if lang=='it' else 'fr'),"likes":lk}
# dedup edges by (amp,q)
seen=set(); ed=[]
for e in sorted(edges,key=lambda x:-x['likes']):
    key=(e['amp'],e['q'].lower())
    if key in seen: continue
    seen.add(key); ed.append(e)
CMP['ampnet']={"edges":ed,"quoters":list(qnodes.values()),
  "amps":[{"h":a['h'],"likes":a['max_likes']} for a in amps if a['h'].lower() in {e['amp'] for e in ed}]}

# ---- hourly heatmap (frame x hour) ----
def hourmat(rows):
    frames=['immigration','hooliganism','police_state','counter','news']
    mat={f:[0]*24 for f in frames}
    for t in rows:
        d=t.get('date','');
        if len(d)<13: continue
        try: hr=int(d[11:13])
        except: continue
        f=t.get('frame','other')
        if f in mat: mat[f][hr]+=1
    hours=sorted({h for f in mat for h in range(24) if mat[f][h]})
    return {"frames":frames,"hours":hours,"mat":{f:[mat[f][h] for h in hours] for f in mat}}
CMP['heat_fr']=hourmat(frd); CMP['heat_it']=hourmat(itd)

json.dump(CMP,open(BASE+"compare.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
open(BASE+"compare_data.js","w",encoding="utf-8").write("window.CMP="+json.dumps(CMP,ensure_ascii=False)+";")
print("FR dom",len(frd),"IT dom",len(itd),"total on-topic",CMP['meta']['total'])
print("FR frames",{k:v['n'] for k,v in CMP['fr']['frames'].items()})
print("IT frames",{k:v['n'] for k,v in CMP['it']['frames'].items()})
print("imm FR",CMP['fr']['imm'],"imm IT",CMP['it']['imm'])
print("avatars resolved FR top:",sum(1 for t in CMP['fr']['top'] if t['av']),"/12  IT top:",sum(1 for t in CMP['it']['top'] if t['av']),"/12")
