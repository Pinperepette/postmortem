#!/usr/bin/env python3
# Calibrazione sondaggi <-> social: i social nella finestra predicono il Delta-voto?
import numpy as np

# --- Serie sondaggi (SWG settimanale, singolo istituto, piu varianza) ---
polls = {
 "2026-03-30": dict(FdI=29.5,PD=22.0,M5S=12.3,FI=7.9,Lega=6.6,AVS=6.6,FN=3.3,Azione=3.4,IV=2.3),
 "2026-04-13": dict(FdI=29.3,PD=21.9,M5S=12.2,FI=7.7,Lega=6.3,AVS=6.6,FN=3.5,Azione=3.5,IV=2.4),
 "2026-04-27": dict(FdI=29.1,PD=21.6,M5S=12.5,FI=7.7,Lega=6.2,AVS=6.7,FN=3.6,Azione=3.4,IV=2.3),
 "2026-05-25": dict(FdI=28.1,PD=22.5,M5S=12.7,FI=7.4,Lega=6.0,AVS=6.6,FN=4.3,Azione=3.5,IV=2.5),
 "2026-06-01": dict(FdI=28.2,PD=22.3,M5S=13.0,FI=7.2,Lega=5.8,AVS=6.7,FN=4.6,Azione=3.4,IV=2.4),
}
dates = list(polls.keys())
# finestra Wk (social) -> Delta voto tra poll k e k+1
win_to_delta = [("W1",0,1),("W2",1,2),("W3",2,3),("W4",3,4)]

leader2party = dict(Meloni="FdI",Schlein="PD",Conte="M5S",Tajani="FI",
                    Salvini="Lega",AVS="AVS",Vannacci="FN",Calenda="Azione",Renzi="IV")

# --- Social storico per (leader, finestra): rate_per_hour, pro, contro, neutro ---
social = {
 "Meloni":  [(22,9,31,35),(27,10,21,46),(17,5,25,47),(14,10,13,50)],
 "Schlein": [(2,6,9,54),(5,8,12,56),(3,8,15,45),(6,4,8,59)],
 "Conte":   [(1,10,19,49),(2,7,30,33),(1,6,21,48),(1,4,11,43)],
 "Tajani":  [(17,8,16,50),(6,7,15,51),(9,9,20,51),(4,8,10,53)],
 "Salvini": [(8,8,27,40),(12,5,20,49),(11,4,15,59),(10,4,11,63)],
 "AVS":     [(1,7,18,44),(2,6,8,58),(2,3,13,44),(2,5,14,39)],
 "Vannacci":[(2,13,13,53),(7,8,10,56),(10,9,13,55),(11,11,17,49)],
 "Calenda": [(3,8,20,46),(6,10,18,48),(3,8,15,54),(1,11,8,53)],
 "Renzi":   [(6,4,16,58),(7,13,8,55),(6,12,14,48),(4,13,12,41)],
}

rows=[]  # (leader, win, sov, polarity, mobil, dvote)
for ld,party in leader2party.items():
    for i,(wn,a,b) in enumerate(win_to_delta):
        sov,pro,con,neu = social[ld][i]
        side = pro+con
        polarity = (pro-con)/side if side>0 else 0.0     # net favorevole tra chi si schiera
        mobil = pro/ (1.0)                                # difensori attivi (campione 80)
        dvote = polls[dates[b]][party]-polls[dates[a]][party]
        rows.append([ld,wn,sov,polarity,mobil,dvote])

import math
L=[r[0] for r in rows]; W=[r[1] for r in rows]
sov=np.array([r[2] for r in rows],float)
pol=np.array([r[3] for r in rows],float)
mob=np.array([r[4] for r in rows],float)
dv =np.array([r[5] for r in rows],float)
logsov=np.log(sov+1)

def zc(x):
    s=x.std();
    return (x-x.mean())/s if s>0 else x*0
# momentum composito (qualita + intensita + volume), standardizzato
momentum = zc(pol)+ zc(logsov)+ zc(mob)

def pearson(x,y):
    if x.std()==0 or y.std()==0: return 0.0,1.0
    r=np.corrcoef(x,y)[0,1]; n=len(x)
    if abs(r)>=1: return r,0.0
    t=r*math.sqrt((n-2)/(1-r*r))
    # p ~ two sided via normal approx
    from math import erf
    p=2*(1-0.5*(1+erf(abs(t)/math.sqrt(2))))
    return r,p

# within-leader (effetti fissi): demean per leader
def within(x):
    x=x.copy().astype(float)
    for ld in set(L):
        idx=[i for i,l in enumerate(L) if l==ld]
        x[idx]=x[idx]-x[idx].mean()
    return x

print("=== POOLED (cross, 36 oss) ===")
for nm,x in [("polarity",pol),("log_sov",logsov),("mobil",mob),("MOMENTUM",momentum)]:
    r,p=pearson(x,dv); print(f"  {nm:9s} vs Dvote: r={r:+.3f}  p={p:.3f}")

print("=== WITHIN-LEADER (effetti fissi: il proprio momentum predice la propria salita?) ===")
dvw=within(dv)
for nm,x in [("polarity",pol),("log_sov",logsov),("mobil",mob),("MOMENTUM",momentum)]:
    r,p=pearson(within(x),dvw); print(f"  d{nm:9s} vs dDvote: r={r:+.3f}  p={p:.3f}")

# regressione within: Dvote ~ momentum (slope = punti-sondaggio per 1 sigma di momentum)
xw=within(momentum); yw=dvw
b=(xw@yw)/(xw@xw) if xw@xw>0 else 0
print(f"\nSlope within (MOMENTUM->Dvote): {b:+.3f} punti per 1 unita momentum")

# scatter data per il report
print("\n=== SCATTER (within momentum, within Dvote) ===")
for i in range(len(rows)):
    print(f"{L[i]:9s} {W[i]} mom={within(momentum)[i]:+.2f} dV={dvw[i]:+.2f}")
