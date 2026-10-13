import json, sys, urllib.request
from collections import Counter
ev=sys.argv[1]
def q(url):
    r=json.loads(urllib.request.urlopen(url).read())["routes"][0]
    nt=sum("toll" in it.get("classes",[]) for s in r["legs"][0]["steps"] for it in s["intersections"])
    return (r["distance"],r["duration"],r["weight"],nt)
U="http://127.0.0.1:5001/route/v1/driving/{}?alternatives=false&steps=true&geometries=polyline&overview=simplified{}"
cases={"26_29":"-3.691978,40.419026;-1.644406,42.818565","16_18":"-3.598691,37.174289;-1.985721,43.321523",
       "26_6_Madrid_Barcelona_ctrl":None}
out={}
for n,c in cases.items():
    if c is None: continue
    for ex in ("","&exclude=toll"):
        out[n+ex]=Counter(map(str,[q(U.format(c,ex)) for _ in range(24)]))
        print(n,ex,dict(out[n+ex]))
json.dump(out,open(f"{ev}/pesos_variantes_2026-10-11.json","w"),indent=1)
