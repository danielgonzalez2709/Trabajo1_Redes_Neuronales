import json, gzip, sys, urllib.request, datetime, pathlib, csv
base=pathlib.Path(sys.argv[1]); ev=sys.argv[2]
def nt(r): return sum("toll" in it.get("classes",[]) for s in r["legs"][0]["steps"] for it in s["intersections"])
rows=[]; t0=datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
for f in sorted(base.glob("*.json.gz")):
    d=json.load(gzip.open(f)); r0=d["respuesta"]["routes"][0]
    url=d["url"].replace(":5001/",":5002/")
    r1=json.loads(urllib.request.urlopen(url).read())["routes"][0]
    rows.append([d["origen"],d["destino"],d["alternativa"],r0["distance"],r0["weight"],nt(r0),r1["distance"],r1["weight"],nt(r1)])
with open(f"{ev}/replay_1081_threads1_2026-10-11.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["i","j","alternativa","dist_t2_3","weight_t2_3","toll_t2_3","dist_threads1","weight_threads1","toll_threads1"]); w.writerows(rows)
t1=datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
for alt in ("rapida","sin_peaje"):
    R=[x for x in rows if x[2]==alt]
    diff=[x for x in R if abs(x[3]-x[6])>0.5]
    print(alt,"n",len(R),"distinta_dist",len(diff),"t2.3_peor_peso",sum(x[4]>x[7]+1e-6 for x in R),"t2.3_mejor_peso",sum(x[4]<x[7]-1e-6 for x in R),
          "toll_t2.3>0",sum(x[5]>0 for x in R),"toll_threads1>0",sum(x[8]>0 for x in R), "max_dif_km",max([abs(x[3]-x[6]) for x in R])/1000)
    if alt=="sin_peaje": print(" pares sin_peaje con toll en threads1:",[(x[0],x[1],x[8]) for x in R if x[8]>0])
print(t0,t1)
