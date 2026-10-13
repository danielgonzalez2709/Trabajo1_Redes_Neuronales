import subprocess, shutil, sys, os, re
S="/tmp/claude-1000/-home-andy-Documentos-Estudio-Universidad-SeptimoSemestre-RedesNeuronales-Trabajo1-Redes-Neuronales/0da19be8-fa23-424b-9237-b44c3dcdaf2c/scratchpad"
PY="/home/andy/Documentos/Estudio/Universidad/SeptimoSemestre/RedesNeuronales/Trabajo1_Redes_Neuronales/.venv/bin/python"
BASE=S+"/mut/base"
src=open(BASE+"/src/part1/de.py").read()
def R(a,b):
    return (a,b)
ASYNC_OLD = src[src.index("            indices_padres = sortear_padres(tamano, rng)\n"):src.index("            # Frame de la generación completada")]
ASYNC_NEW = '''            indices_padres = sortear_padres(tamano, rng)
            poblacion = poblacion.copy(); aptitudes = aptitudes.copy()
            for i in range(tamano):
                mut = mutar_diferencial(poblacion, indices_padres, parametros.factor_f)[i:i+1]
                mut = reiniciar_fuera_de_dominio(mut, limites, rng).mutantes
                hij = cruzar_binomial(poblacion[i:i+1], mut, parametros.prob_cruce, rng).hijos
                fh = problem.f(hij[0])
                if fh <= aptitudes[i]:
                    poblacion[i] = hij[0]; aptitudes[i] = fh
'''
M10_OLD = '''            reinicio = reiniciar_fuera_de_dominio(mutantes, limites, rng)

            # `cruzar_binomial`: cruce con el padre; hijos (NP, d).
            cruce = cruzar_binomial(poblacion, reinicio.mutantes, parametros.prob_cruce, rng)
'''
M10_NEW = '''            cruce = cruzar_binomial(poblacion, mutantes, parametros.prob_cruce, rng)
            class _C: pass
            _h = reiniciar_fuera_de_dominio(cruce.hijos, limites, rng).mutantes
            cruce = ResultadoCruce(hijos=_h, de_mutante=cruce.de_mutante)
'''
muts = {
"M1 sel <= -> <": [("reemplazaron = aptitudes_hijos <= aptitudes","reemplazaron = aptitudes_hijos < aptitudes")],
"M2 nunca reemplaza": [("reemplazaron = aptitudes_hijos <= aptitudes","reemplazaron = np.zeros(aptitudes.shape, dtype=bool)")],
"M3 siempre reemplaza": [("reemplazaron = aptitudes_hijos <= aptitudes","reemplazaron = np.ones(aptitudes.shape, dtype=bool)")],
"M4 sin j_rand": [("de_mutante = (uniformes <= prob_cruce) | es_gen_obligatorio","de_mutante = (uniformes <= prob_cruce)")],
"M5 j_rand fijo 0 (consume rng)": [("columna_obligatoria = rng.integers(0, dimension, size=tamano)","columna_obligatoria = rng.integers(0, dimension, size=tamano) * 0")],
"M6 padres pueden incluir i": [("    np.fill_diagonal(sorteo, np.inf)\n","")],
"M7 padres indep. con repeticion (!= i)": [("    indices_padres = orden_por_fila[:, :PADRES_POR_INDIVIDUO]        # forma (NP, 3)\n    return indices_padres",
   "    indices_padres = (np.arange(tamano)[:, None] + 1 + rng.integers(0, tamano - 1, size=(tamano, 3))) % tamano\n    return indices_padres")],
"M7b r2 = r3": [("    indices_padres = orden_por_fila[:, :PADRES_POR_INDIVIDUO]        # forma (NP, 3)\n    return indices_padres",
   "    indices_padres = orden_por_fila[:, :PADRES_POR_INDIVIDUO].copy(); indices_padres[:, 2] = indices_padres[:, 1]\n    return indices_padres")],
"M8 F<->CR": [("mutar_diferencial(poblacion, indices_padres, parametros.factor_f)","mutar_diferencial(poblacion, indices_padres, parametros.prob_cruce)"),
              ("cruzar_binomial(poblacion, reinicio.mutantes, parametros.prob_cruce, rng)","cruzar_binomial(poblacion, reinicio.mutantes, parametros.factor_f, rng)")],
"M9 clip en vez de reinicio (consume rng)": [("mutantes_nuevos = np.where(reiniciadas, sorteo, mutantes)","mutantes_nuevos = np.clip(mutantes, limites_inferiores, limites_superiores)")],
"M10 reinicio sobre el hijo post-cruce": [(M10_OLD,M10_NEW)],
"M11 U<=CR -> U<CR": [("(uniformes <= prob_cruce)","(uniformes < prob_cruce)")],
"M12 best/1": [("            reinicio = reiniciar_fuera_de_dominio(mutantes, limites, rng)\n",
   "            mutantes = mutantes - poblacion[indices_padres[:, 0]] + poblacion[np.argmin(aptitudes)]\n            reinicio = reiniciar_fuera_de_dominio(mutantes, limites, rng)\n")],
"M13 asincrono": [(ASYNC_OLD,ASYNC_NEW)],
"M14 truncada registrada como frame": [("        # Presupuesto agotado: la generación incompleta no registra frame y el mejor punto\n        # visto está en problem.best_x / problem.best_f.\n        pass",
   "        if guardar_frames and frames:\n            _registrar_frame(frames, generacion, poblacion, aptitudes)")],
"M14b truncada actualiza poblacion/frames (hijos parciales)": [("            aptitudes_hijos = evaluar_poblacion(cruce.hijos, problem.f)     # forma (NP,)",
   "            aptitudes_hijos = np.full(tamano, np.inf)\n            try:\n                for _i in range(tamano): aptitudes_hijos[_i] = problem.f(cruce.hijos[_i])\n            except BudgetExhausted:\n                _s = seleccionar_codiciosa(poblacion, aptitudes, cruce.hijos, aptitudes_hijos)\n                if guardar_frames: _registrar_frame(frames, generacion, _s.poblacion, _s.aptitudes)\n                raise")],
"M15 NP<4 aceptado": [("POBLACION_MINIMA = PADRES_POR_INDIVIDUO + 1 ","POBLACION_MINIMA = PADRES_POR_INDIVIDUO ")],
"M16 dominio exclusivo": [("reiniciadas = (mutantes < limites_inferiores) | (mutantes > limites_superiores)","reiniciadas = (mutantes <= limites_inferiores) | (mutantes >= limites_superiores)")],
"M17a rng: j_rand antes de U": [("    uniformes = rng.random((tamano, dimension))\n","    columna_obligatoria = rng.integers(0, dimension, size=tamano)\n    uniformes = rng.random((tamano, dimension))\n"),
   ("    columna_obligatoria = rng.integers(0, dimension, size=tamano)\n\n","\n")],
"M17b rng: sorteo de reinicio de valor no uniforme (rng.random sin escalar)": [("sorteo = rng.uniform(limites_inferiores, limites_superiores, size=mutantes.shape)","sorteo = rng.uniform(limites_inferiores, limites_superiores, size=mutantes.shape) * 0.5 + limites_inferiores * 0.5")],
"M18 poblacion inicial evaluada 2 veces": [("        aptitudes = evaluar_poblacion(poblacion, problem.f)          # forma (NP,)\n","        aptitudes = evaluar_poblacion(poblacion, problem.f)\n        aptitudes = evaluar_poblacion(poblacion, problem.f)\n")],
"M19 generaciones T -> T+1 (<=)": [("generacion < parametros.generaciones","generacion <= parametros.generaciones")],
"M20 frame best = argmax": [("mejor = poblacion[np.argmin(aptitudes)]","mejor = poblacion[np.argmax(aptitudes)]")],
"M21 j_rand nunca el ultimo gen": [("rng.integers(0, dimension, size=tamano)\n\n    # Índice","rng.integers(0, max(dimension - 1, 1), size=tamano)\n\n    # Índice")],
"M22 mutacion r2 + r3": [("diferencia = extremo_r2 - extremo_r3","diferencia = extremo_r2 + extremo_r3")],
"M23 n_grad/eval_equiv: n_f mal (n_f+1)": [('"n_f": int(problem.n_f),','"n_f": int(problem.n_f) + 1,')],
"M24 reinicio solo limite superior": [("(mutantes < limites_inferiores) | (mutantes > limites_superiores)","(mutantes > limites_superiores)")],
"M25 reinicio con limites de dim 0 para todas": [("sorteo = rng.uniform(limites_inferiores, limites_superiores, size=mutantes.shape)","sorteo = rng.uniform(limites_inferiores[0], limites_superiores[0], size=mutantes.shape)")],
"M26 mutacion con poblacion a medias (r1 desde hijos previos): F aplicada a r1": [("mutantes = base_r1 + factor_f * diferencia","mutantes = factor_f * (base_r1 + diferencia)")],
}
only = sys.argv[1:] 
for name, reps in muts.items():
    if only and not any(name.startswith(o) for o in only): continue
    d=S+"/mut/work"
    if os.path.exists(d): shutil.rmtree(d)
    shutil.copytree(BASE,d)
    s=src
    for a,b in reps:
        assert s.count(a)==1,(name,a[:50],s.count(a))
        s=s.replace(a,b)
    open(d+"/src/part1/de.py","w").write(s)
    chk=subprocess.run([PY,"-c","import src.part1.de as m;print(m.__file__)"],cwd=d,capture_output=True,text=True).stdout.strip()
    assert chk.startswith(d),chk
    r=subprocess.run([PY,"-m","pytest","tests/test_de.py","-q","-x","-p","no:cacheprovider"],cwd=d,capture_output=True,text=True)
    tail=r.stdout.strip().splitlines()
    fails=[l for l in tail if l.startswith("FAILED")]
    print(f"{name}: {'MUERTO' if r.returncode!=0 else 'SOBREVIVE'} | {fails[0][:150] if fails else tail[-1]}",flush=True)
