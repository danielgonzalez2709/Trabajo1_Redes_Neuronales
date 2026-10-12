import json, sys, urllib.request
ev=sys.argv[1]
U="http://127.0.0.1:5001/route/v1/driving/{}?alternatives=false&steps=true&geometries=geojson&overview=full&annotations=nodes&exclude=toll"
cases={"26_29":"-3.691978,40.419026;-1.644406,42.818565","16_18":"-3.598691,37.174289;-1.985721,43.321523"}
for n,c in cases.items():
    got={}
    for _ in range(30):
        raw=urllib.request.urlopen(U.format(c)).read(); r=json.loads(raw)["routes"][0]
        nt=sum("toll" in it.get("classes",[]) for s in r["legs"][0]["steps"] for it in s["intersections"])
        got.setdefault(nt,(raw,r))
        if len(got)==2: break
    for nt,(raw,r) in got.items():
        open(f"{ev}/osrm_{n}_sin_peaje_nodes_variante_toll{nt}_2026-10-11.json","wb").write(raw)
    r=got[max(got)][1]; leg=r["legs"][0]; coords=r["geometry"]["coordinates"]; nodes=leg["annotation"]["nodes"]
    idx={}
    for k,cc in enumerate(coords): idx.setdefault((round(cc[0],6),round(cc[1],6)),[]).append(k)
    allids=[]
    for si,s in enumerate(leg["steps"]):
        for it in s["intersections"]:
            if "toll" in it.get("classes",[]):
                ks=idx.get((round(it["location"][0],6),round(it["location"][1],6)),[])
                pr=[(nodes[k],nodes[k+1]) for k in ks if k+1<len(nodes)]
                allids+= [x for p in pr for x in p]
                print(n,"step",si,s.get("ref"),it["location"],"node->next",pr)
    print(n,"IDS",sorted(set(allids)))
    # diff of step sequences
    a=[(s.get("ref"),s.get("name"),round(s["distance"])) for s in got[max(got)][1]["legs"][0]["steps"]]
    b=[(s.get("ref"),s.get("name"),round(s["distance"])) for s in got[min(got)][1]["legs"][0]["steps"]]
    i=0
    while a[i]==b[i]: i+=1
    j=1
    while a[-j]==b[-j]: j+=1
    print(n,"variant con toll:",a[i-1:len(a)-j+2]); print(n,"variant sin toll:",b[i-1:len(b)-j+2])
