import sys, math, itertools, collections; sys.path.insert(0,".")
import numpy as np
from src.part1.de import *
from src.part1.de import sortear_padres, cruzar_binomial, reiniciar_fuera_de_dominio
from src.common.counter import CountedProblem
from src.part1.functions import get_function, FUNCIONES
sys.path.insert(0,"/tmp/claude-1000/-home-andy-Documentos-Estudio-Universidad-SeptimoSemestre-RedesNeuronales-Trabajo1-Redes-Neuronales/0da19be8-fa23-424b-9237-b44c3dcdaf2c/scratchpad")
from ref_de import ref
def pchi(chi, df):  # Wilson-Hilferty upper tail
    z = ((chi/df)**(1/3) - (1-2/(9*df)))/math.sqrt(2/(9*df)); return 0.5*math.erfc(z/math.sqrt(2))
rng = np.random.default_rng(7)
# B1 parents
for NP in (4,6,30):
    N=200000 if NP<30 else 100000
    cnt = {i: collections.Counter() for i in range(NP)}
    bad=0
    for _ in range(N//NP+1):
        P = sortear_padres(NP, rng)
        for i in range(NP):
            t = tuple(P[i]); 
            if len(set(t))<3 or i in t: bad+=1
            if NP<=6: cnt[i][t]+=1
    if NP<=6:
        k=(NP-1)*(NP-2)*(NP-3); 
        worst=1
        for i in range(NP):
            n=sum(cnt[i].values()); assert len(cnt[i])==k, (len(cnt[i]),k)
            chi=sum((c-n/k)**2/(n/k) for c in cnt[i].values()); worst=min(worst,pchi(chi,k-1))
        print("NP",NP,"triples ordenadas",k,"invalidas",bad,"min p chi2 sobre filas",round(worst,3),"n por fila",n)
    else:
        # marginals for row 5: each of 29 values equally likely per slot
        c=np.zeros((3,NP)); n=0
        for _ in range(N//NP+1):
            P=sortear_padres(NP,rng); 
            for s in range(3): c[s]+=np.bincount(P[5,s:s+1],minlength=NP)
            n+=1
        e=n/(NP-1); chis=[sum((c[s,j]-e)**2/e for j in range(NP) if j!=5) for s in range(3)]
        print("NP",NP,"invalidas",bad,"p marginales por slot",[round(pchi(x,NP-2),3) for x in chis],"c[s,5]",c[:,5])
# B2 crossover
for d in (2,3):
  for CR in (0.0,0.3,0.9,1.0):
    NP=1000; fr=[]
    for _ in range(300):
        x=np.zeros((NP,d)); v=np.ones((NP,d))
        r=cruzar_binomial(x,v,CR,rng); h=r.hijos
        assert (h.sum(1)>=1).all()
        fr.append(h.mean())
    exp = CR+(1-CR)/d
    print("d",d,"CR",CR,"frac mutante obs",round(np.mean(fr),4),"esp CR+(1-CR)/d =",round(exp,4), "CR=1 hijo==mutante", CR!=1 or (h==1).all())
# B3 reinicio
lim=np.array([[-2.048,2.048],[-2.048,2.048]])
m=np.array([[-2.048,2.048],[-2.0480000001,0.],[2.0480000001,5.],[0.,0.]])
r=reiniciar_fuera_de_dominio(m,lim,rng)
print("reinicio mascara\n",r.reiniciadas.astype(int).tolist(),"\n en dominio", ((r.mutantes>=-2.048)&(r.mutantes<=2.048)).all(), "borde conservado", r.mutantes[0].tolist())
big=rng.normal(size=(100000,2))*10; r=reiniciar_fuera_de_dominio(big,lim,rng); print("100k mutantes dentro:", ((r.mutantes>=-2.048)&(r.mutantes<=2.048)).all())
# B4 count + monotone + domain
class Inst:
    def __init__(s,f): s.f_=f; s.dim=f.dim; s.bounds=f.bounds; s.x_star=f.x_star; s.f_star=f.f_star; s.out=0; s.n=0
    def f(s,x):
        x=np.asarray(x); lb,ub=s.bounds[:,0],s.bounds[:,1]; s.n+=1
        if ((x<lb)|(x>ub)).any() or not np.isfinite(x).all(): s.out+=1
        return s.f_.f(x)
    def grad(s,x): return s.f_.grad(x)
for fn in ("rosenbrock","rastrigin"):
  for d,B,T in ((2,20000,None),(3,30000,None),(2,10**9,50),(3,10**9,17),(2,30*10,None),(2,31,None),(2,59,None),(2,60,None)):
    for k in (2*d,1):
        fo=Inst(get_function(fn,d)); p=CountedProblem(fo,k,B if B<10**9 else 10**8)
        mono=[]
        cfg={"de":{"NP":30,"F":0.7,"CR":0.9,"generaciones":T},"record_frames":True}
        from src.part1.de import optimize
        r=optimize(p,cfg,np.random.default_rng(3))
        fr=r.get("frames",[]); 
        h=[x["f_best"] for x in r["history"]]
        pos_ok=all(all(a>=b for a,b in zip(h[:-1],h[1:])) for _ in [0])
        print(fn,d,"B",B,"T",T,"k",k,"n_f",r["n_f"],"n_grad",r["n_grad"],"eq",r["eval_equiv"],"frames",len(fr),"lastiter",fr[-1]["iter"] if fr else None,"fuera_dominio",fo.out,"hist monot",pos_ok, "evals instr",fo.n)
        if k==2*d and fn=="rosenbrock" and False: pass
# B5 population fitness never worsens (hook in ref) 
worse=0
for fn in FUNCIONES:
  for d in (2,3):
    prev=[None]
    def hook(g,x,fx,prev=prev):
        global worse
        if prev[0] is not None and (fx>prev[0]).any(): worse+=1
        prev[0]=fx.copy()
    p=CountedProblem(get_function(fn,d),2*d,10000*d)
    ref(p,30,0.7,0.9,np.random.default_rng(11),hook=hook)
print("generaciones donde aptitud de algun puesto empeora:",worse)
