import json, sys, urllib.request, datetime, hashlib, pathlib
out = pathlib.Path(sys.argv[1])
cases = {"16_18": ((-3.598691,37.174289),(-1.985721,43.321523)),
         "26_29": ((-3.691978,40.419026),(-1.644406,42.818565))}
for name,(a,b) in cases.items():
    for excl in ("exclude=toll",""):
        url=(f"http://127.0.0.1:5001/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}"
             f"?alternatives=false&steps=true&geometries=geojson&overview=full&annotations=nodes" + (("&"+excl) if excl else ""))
        raw=urllib.request.urlopen(url).read()
        tag="sin_peaje" if excl else "rapida"
        fn=out/f"osrm_{name}_{tag}_nodes_2026-10-11.json"
        fn.write_bytes(raw)
        d=json.loads(raw); r=d["routes"][0]; leg=r["legs"][0]
        coords=r["geometry"]["coordinates"]; nodes=leg["annotation"]["nodes"]
        print("==",name,tag,url, "dist",r["distance"], "ncoords",len(coords),"nnodes",len(nodes), datetime.datetime.utcnow().isoformat())
        if not excl: continue
        idx={}
        for k,c in enumerate(coords): idx.setdefault((round(c[0],6),round(c[1],6)),[]).append(k)
        for si,s in enumerate(leg["steps"]):
            for it in s["intersections"]:
                if "toll" in it.get("classes",[]):
                    loc=(round(it["location"][0],6),round(it["location"][1],6))
                    ks=idx.get(loc,[])
                    pairs=[(nodes[k],nodes[k+1] if k+1<len(nodes) else None) for k in ks]
                    print(f" step {si} ref={s.get('ref')} name={s.get('name')!r} loc={loc} classes={it['classes']} in={it.get('in')} out={it.get('out')} bearings={it.get('bearings')} node->next={pairs}")
