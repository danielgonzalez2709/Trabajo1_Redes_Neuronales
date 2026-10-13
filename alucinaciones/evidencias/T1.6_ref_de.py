import sys, numpy as np
from src.common.counter import CountedProblem, BudgetExhausted
from src.common.seeds import make_rng
from src.part1.functions import get_function

def ref(problem, NP, F, CR, rng, T=None, frames_on=True, hook=None):
    b = np.asarray(problem.func.bounds, float); lb, ub = b[:,0], b[:,1]; d = len(lb)
    frames = []; gens_done = 0
    try:
        x = rng.uniform(lb, ub, size=(NP, d))
        fx = np.array([problem.f(x[i]) for i in range(NP)])
        if frames_on and d == 2:
            frames.append({"iter":0,"positions":x.tolist(),"best":x[np.argmin(fx)].tolist()})
        g = 0
        while T is None or g < T:
            g += 1
            M = rng.random((NP, NP)); M[np.arange(NP), np.arange(NP)] = np.inf
            par = np.argsort(M, axis=1)[:, :3]
            v = x[par[:,0]] + F*(x[par[:,1]] - x[par[:,2]])
            R = rng.uniform(lb, ub, size=(NP, d))
            out = (v < lb) | (v > ub)
            v = np.where(out, R, v)
            U = rng.random((NP, d))
            j = rng.integers(0, d, size=NP)
            u = np.where((U <= CR) | (np.arange(d)[None,:] == j[:,None]), v, x)
            fu = np.array([problem.f(u[i]) for i in range(NP)])
            rep = fu <= fx
            x = np.where(rep[:,None], u, x); fx = np.where(rep, fu, fx)
            gens_done = g
            if hook: hook(g, x, fx)
            if frames_on and d == 2:
                frames.append({"iter":g,"positions":x.tolist(),"best":x[np.argmin(fx)].tolist()})
    except BudgetExhausted:
        pass
    return {"x_best": problem.best_x.tolist(), "f_best": float(problem.best_f), "n_f": problem.n_f,
            "n_grad": problem.n_grad, "eval_equiv": problem.eval_equiv(),
            "history": [dict(h) for h in problem.history], "frames": frames, "gens": gens_done}
