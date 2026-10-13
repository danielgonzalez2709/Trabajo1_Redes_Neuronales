import json, gzip, sys, urllib.request, datetime
from collections import Counter
base=sys.argv[1]; ev=sys.argv[2]
def q(url):
    r=json.loads(urllib.request.urlopen(url).read())["routes"][0]
    nt=sum("toll" in it.get("classes",[]) for s in r["legs"][0]["steps"] for it in s["intersections"])
    return (r["distance"],nt)
log={"inicio_utc":datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")}
for name in ("26_29","16_18"):
    url=json.load(gzip.open(f"{base}/{name}_sin_peaje.json.gz"))["url"]
    rap=url.replace("&exclude=toll","")
    seq=[q(url) for _ in range(30)]
    alt=[]
    for _ in range(15):
        q(rap); alt.append(q(url))
    log[name]={"url":url,"repetidas_30":Counter(map(str,seq)),"tras_rapida_15":Counter(map(str,alt)),"rapida_5":Counter(map(str,[q(rap) for _ in range(5)]))}
    print(name, log[name])
# other pairs: 1081 not feasible; check Madrid->Barcelona control
log["fin_utc"]=datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
json.dump(log,open(f"{ev}/repeticiones_2026-10-11.json","w"),indent=1,default=dict)
