import sys; sys.path.insert(0,".")
import numpy as np
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.part1.functions import get_function
from src.part1.de import optimize
for base in (0,1000,12345):
  for fn in ("rosenbrock","rastrigin"):
    for d in (2,3):
        s=0; fails=[]
        for r in range(30):
            p=CountedProblem(get_function(fn,d),2*d,10000*d)
            o=optimize(p,{"de":{"NP":30,"F":0.7,"CR":0.9,"generaciones":None},"record_frames":False},make_rng(base,r))
            ok=o["f_best"]-get_function(fn,d).f_star<=1e-4; s+=ok
            if not ok: fails.append(round(o["f_best"],4))
        print("base",base,fn,d,s,"/30",fails)
