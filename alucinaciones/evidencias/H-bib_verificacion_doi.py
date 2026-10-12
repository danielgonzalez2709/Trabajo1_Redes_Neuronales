"""Verificación de la bibliografía del blog contra doi.org / Crossref (12-oct-2026).

Paso 1 (antes de consultar nada): Claude Opus 5.5 escribió DE MEMORIA la lista REFERENCIAS_DE_MEMORIA,
con el DOI, los autores, el año y la revista que "recordaba" para cada referencia clave del proyecto.
Paso 2: este script consulta https://api.crossref.org/works/<doi> y compara lo recordado con lo registrado.
Cualquier discrepancia es un candidato para la Cacería de la alucinación (categoría Bibliografía).

Uso (con internet; no forma parte de los experimentos):
    .venv\\Scripts\\python.exe alucinaciones/evidencias/H-bib_verificacion_doi.py
"""
import json
import urllib.request

REFERENCIAS_DE_MEMORIA = [
    # clave, doi, primer autor (apellido), año, contenedor esperado
    ("kennedy1995", "10.1109/ICNN.1995.488968", "Kennedy", 1995, "Proceedings of ICNN'95"),
    ("shi1998", "10.1109/ICEC.1998.699146", "Shi", 1998, "IEEE World Congress on Computational Intelligence"),
    ("clerc2002", "10.1109/4235.985692", "Clerc", 2002, "IEEE Transactions on Evolutionary Computation"),
    ("storn1997", "10.1023/A:1008202821328", "Storn", 1997, "Journal of Global Optimization"),
    ("dorigo1996", "10.1109/3477.484436", "Dorigo", 1996, "IEEE Transactions on Systems, Man, and Cybernetics, Part B"),
    ("dorigo1997", "10.1109/4235.585892", "Dorigo", 1997, "IEEE Transactions on Evolutionary Computation"),
    ("stutzle2000", "10.1016/S0167-739X(00)00043-1", "Stützle", 2000, "Future Generation Computer Systems"),
    ("rosenbrock1960", "10.1093/comjnl/3.3.175", "Rosenbrock", 1960, "The Computer Journal"),
    ("armijo1966", "10.2140/pjm.1966.16.1", "Armijo", 1966, "Pacific Journal of Mathematics"),
    ("dantzig1954", "10.1287/opre.2.4.393", "Dantzig", 1954, "Operations Research"),
    ("berahas2022", "10.1007/s10208-021-09513-z", "Berahas", 2022, "Foundations of Computational Mathematics"),
]


def crossref(doi):
    url = "https://api.crossref.org/works/" + doi
    req = urllib.request.Request(url, headers={"User-Agent": "Trabajo1-UNAL (verificacion bibliografia)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)["message"]
    except Exception as exc:  # noqa: BLE001 - se reporta cualquier fallo como "no resuelve"
        return {"error": f"{type(exc).__name__}: {exc}"}


for clave, doi, autor, anio, contenedor in REFERENCIAS_DE_MEMORIA:
    m = crossref(doi)
    if "error" in m:
        print(f"[NO RESUELVE] {clave} doi={doi} -> {m['error']}")
        continue
    autores = [a.get("family", "") for a in m.get("author", [])]
    anio_reg = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
    cont = (m.get("container-title") or [""])[0]
    titulo = (m.get("title") or [""])[0]
    ok_autor = bool(autores) and autores[0].lower() == autor.lower()
    ok_anio = anio_reg == anio
    marca = "OK" if (ok_autor and ok_anio) else "DISCREPANCIA"
    print(f"[{marca}] {clave} doi={doi}\n    recordado: {autor}, {anio}, {contenedor}\n"
          f"    registrado: {', '.join(autores)}; {anio_reg}; {cont}\n    título: {titulo}")
