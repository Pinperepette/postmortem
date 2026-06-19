#!/usr/bin/env python3
# Previsione: estrapolazione del trend (serie SWG) ancorata al livello attuale (Supermedia 18/6)
import numpy as np

# SWG, giorni dal 30/3
days = np.array([0,14,28,56,63],float)
swg = {
 "FdI":[29.5,29.3,29.1,28.1,28.2], "PD":[22.0,21.9,21.6,22.5,22.3],
 "M5S":[12.3,12.2,12.5,12.7,13.0], "FI":[7.9,7.7,7.7,7.4,7.2],
 "Lega":[6.6,6.3,6.2,6.0,5.8], "AVS":[6.6,6.6,6.7,6.6,6.7],
 "FN":[3.3,3.5,3.6,4.3,4.6], "Azione":[3.4,3.5,3.4,3.5,3.4], "IV":[2.3,2.4,2.3,2.5,2.4],
}
# livello attuale (Supermedia 18/6) = giorno 80
now_day=80
now={"FdI":28.2,"PD":21.7,"M5S":12.7,"FI":7.9,"Lega":6.5,"AVS":6.4,"FN":4.9,"Azione":3.0,"IV":2.3}
leader={"FdI":"Meloni","PD":"Schlein","M5S":"Conte","FI":"Tajani","Lega":"Salvini",
        "AVS":"Fratoianni/Bonelli","FN":"Vannacci","Azione":"Calenda","IV":"Renzi"}

# trend "vero" su 3 mesi (incl. dato attuale come 6° punto)
all_days=np.append(days,now_day)
def slope_per_month(party):
    y=np.array(swg[party]+[now[party]],float)
    A=np.vstack([all_days,np.ones_like(all_days)]).T
    m,_=np.linalg.lstsq(A,y,rcond=None)[0]
    return m*30  # punti al mese

H=30  # orizzonte: +1 mese (~mid luglio)
print(f"{'Partito':8s} {'oggi':>6s} {'trend/mese':>10s} {'+1 mese':>9s}  range")
proj={}
for p in now:
    s=slope_per_month(p)
    f=now[p]+s*(H/30)
    proj[p]=f
    print(f"{p:8s} {now[p]:6.1f} {s:+10.2f} {f:9.1f}  [{f-1.0:.1f}-{f+1.0:.1f}]  ({leader[p]})")

print("\n-- coalizioni (proiezione +1 mese, +NM~1.0 +Eu~1.4) --")
cdx=proj['FdI']+proj['FI']+proj['Lega']+1.0
cl =proj['PD']+proj['M5S']+proj['AVS']+proj['IV']+1.4
print(f"Centrodestra ~{cdx:.1f}  |  Campo largo ~{cl:.1f}  |  FN(fuori) ~{proj['FN']:.1f}  |  Azione ~{proj['Azione']:.1f}")
print(f"\nSorpasso FN-Lega: oggi FN {now['FN']} vs Lega {now['Lega']}; +1 mese FN {proj['FN']:.1f} vs Lega {proj['Lega']:.1f}")
