import sys; sys.path.insert(0, ".")
import numpy as np
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.part1.functions import get_function
from src.part1.de import optimize
sys.path.insert(0, "/tmp/claude-1000/-home-andy-Documentos-Estudio-Universidad-SeptimoSemestre-RedesNeuronales-Trabajo1-Redes-Neuronales/0da19be8-fa23-424b-9237-b44c3dcdaf2c/scratchpad")
from ref_de import ref
import itertools
res = {}
for fn, d in itertools.product(["rosenbrock","rastrigin"],[2,3]):
    ok = 0; bad = []; succ = 0; fs=[]
    for s in range(30):
        cfg = {"de":{"NP":30,"F":0.7,"CR":0.9,"generaciones":None}, "record_frames": True}
        p1 = CountedProblem(get_function(fn,d), 2*d, 10000*d)
        a = optimize(p1, cfg, np.random.default_rng(1000+s))
        p2 = CountedProblem(get_function(fn,d), 2*d, 10000*d)
        b = ref(p2, 30, 0.7, 0.9, np.random.default_rng(1000+s))
        same = (a["x_best"]==b["x_best"] and a["f_best"]==b["f_best"] and a["n_f"]==b["n_f"]
                and a["n_grad"]==b["n_grad"] and a["eval_equiv"]==b["eval_equiv"] and a["history"]==b["history"]
                and a.get("frames",[])==b["frames"] if d==2 else
                a["x_best"]==b["x_best"] and a["f_best"]==b["f_best"] and a["n_f"]==b["n_f"] and a["history"]==b["history"] and "frames" not in a)
        if same: ok += 1
        else: bad.append(s)
        fstar = get_function(fn,d).f_star
        succ += (a["f_best"]-fstar <= 1e-4); fs.append(a["f_best"])
    print(fn,d,"coinciden",ok,"/30 bad",bad,"exitos",succ,"/30 n_f",a["n_f"],"frames",len(a.get("frames",[])),
          "ultimo iter", a["frames"][-1]["iter"] if "frames" in a else None, "mediana f", np.median(fs), "max f", max(fs))
