import json, gzip, sys
from collections import Counter
base=sys.argv[1]; ev=sys.argv[2]
for name in ("16_18","26_29"):
    old=json.load(gzip.open(f"{base}/{name}_sin_peaje.json.gz"))
    r=old["respuesta"]["routes"][0]
    new=json.load(open(f"{ev}/osrm_{name}_sin_peaje_nodes_2026-10-11.json"))["routes"][0]
    print(name,"old",r["distance"],r["duration"],r["weight"],"new",new["distance"],new["duration"],new["weight"], "url", old["url"])
    for lab,rr in (("old",r),("new",new)):
        c=Counter(); 
        for s in rr["legs"][0]["steps"]:
            for it in s["intersections"]:
                for k in it.get("classes",[]): c[k]+=1
        print(" ",lab,dict(c))
    for si,s in enumerate(r["legs"][0]["steps"]):
        for it in s["intersections"]:
            if "toll" in it.get("classes",[]):
                print("   old step",si,s.get("ref"),repr(s.get("name")),it["location"],it["classes"],"in",it.get("in"),"out",it.get("out"),it.get("bearings"),it.get("entry"))
