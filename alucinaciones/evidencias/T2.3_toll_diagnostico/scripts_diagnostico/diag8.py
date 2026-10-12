import json, sys, urllib.request, datetime, time
ev=sys.argv[1]
pairs={"AP-15":[(197737868,252287368),(195888050,847869921),(4567432118,13342994276),(195890283,329315555),(621881291,13730570793),(13730570793,10859855063),(7983043581,313241618),(266229237,12507515480)],
       "M-12":[(21281916,1120435368),(1120435333,357411494),(260752321,13245359005),(394942605,8145830536),(1315937318,391105064),(412162761,3609140477)]}
H={"User-Agent":"T2.3-diagnostico-universidad"}
def get(u):
    time.sleep(1); return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60).read()
res={"consulta_utc":datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),"ways":{},"pares":{}}
for tramo,pp in pairs.items():
    for a,b in pp:
        u=f"https://api.openstreetmap.org/api/0.6/node/{a}/ways.json"
        d=json.loads(get(u))
        for w in d["elements"]:
            nd=w["nodes"]
            if any((nd[k],nd[k+1]) in ((a,b),(b,a)) for k in range(len(nd)-1)):
                res["ways"][w["id"]]=w; res["pares"][f"{tramo} {a}-{b}"]=w["id"]
                t=w["tags"]
                print(tramo,(a,b),"way",w["id"],"v",w["version"],w["timestamp"],{k:t[k] for k in t if k in("highway","ref","name","toll","oneway","operator","maxspeed")or k.startswith("toll")})
json.dump(res,open(f"{ev}/osm_api_ways_actual_2026-10-11.json","w"),indent=1)
