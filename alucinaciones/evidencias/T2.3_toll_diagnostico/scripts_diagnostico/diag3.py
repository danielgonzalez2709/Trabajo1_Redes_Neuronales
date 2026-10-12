import json, gzip, sys, urllib.request, hashlib, datetime
base=sys.argv[1]; ev=sys.argv[2]
for name in ("16_18","26_29","16_35","16_44","27_35"):
    old=json.load(gzip.open(f"{base}/{name}_sin_peaje.json.gz"))
    url=old["url"]
    res=[]
    for k in range(3):
        raw=urllib.request.urlopen(url).read(); d=json.loads(raw); r=d["routes"][0]
        nt=sum("toll" in it.get("classes",[]) for s in r["legs"][0]["steps"] for it in s["intersections"])
        res.append((r["distance"],r["duration"],nt))
    if name in ("16_18","26_29"):
        open(f"{ev}/osrm_{name}_sin_peaje_url_original_2026-10-11.json","wb").write(raw)
    print(name, "old", old["respuesta"]["routes"][0]["distance"], old["fecha_consulta_utc"], "data_version old", old["respuesta"].get("data_version"), "| now", res, "data_version", d.get("data_version"), datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"))
