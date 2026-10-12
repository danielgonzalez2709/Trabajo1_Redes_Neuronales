"""Citas literales de las transcripciones de Claude Code para los candidatos de T2.4 (cazador, 2026-10-12).

Las transcripciones no se versionan; viven en ~/.claude/projects/<proyecto>/ en la máquina de Jose Miguel.
Uso (desde la raíz del repositorio):
    .venv/Scripts/python.exe -I alucinaciones/evidencias/T2.4_extractos.py > alucinaciones/evidencias/T2.4_extractos.txt
"""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path.home() / ".claude/projects/C--Users-Jose-Miguel-Documents-ia-Trabajo1-Redes-Neuronales"
RONDA2 = BASE / "cd4116ca-a934-4183-9973-a437cee193f4/subagents/agent-a899138679be750ed.jsonl"
CURADOR = BASE / "6b33b42c-ff37-4f64-854f-9a8625198824/subagents/agent-aeeee1804aa69cf69.jsonl"
REVISOR = BASE / "6b33b42c-ff37-4f64-854f-9a8625198824/subagents/agent-a35160cedf3b10388.jsonl"


def lineas(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]


def texto(o):
    c = o.get("message", {}).get("content", [])
    if isinstance(c, str):
        return c
    partes = []
    for x in c:
        if x.get("type") == "text":
            partes.append(x["text"])
        elif x.get("type") == "tool_use":
            partes.append(json.dumps(x["input"], ensure_ascii=False))
        elif x.get("type") == "tool_result":
            partes.append(json.dumps(x.get("content"), ensure_ascii=False))
    return "\n".join(partes)


def extracto(p, n, aguja, antes=300, despues=300):
    o = lineas(p)[n - 1]
    t = texto(o)
    i = t.find(aguja)
    print(f"[{p.name}, línea {n}, {o.get('timestamp')}, rol {o.get('message', {}).get('role')}]")
    print(t[max(0, i - antes): i + len(aguja) + despues] if i >= 0 else "(no encontrado)")
    print()


for p in (RONDA2, CURADOR, REVISOR):
    print(f"SHA-256 {p.name}: {hashlib.sha256(p.read_bytes()).hexdigest()}")
print()

print("## A. Agente que recibió el prompt 'Ronda 2' de prompts/T2.4.md (primer mensaje):")
print(texto(lineas(RONDA2)[0])[:240], "\n")
print("## A1. Tarifas de la AP-9 que escribió en scripts/construir_peajes.py (tool_use Write):")
extracto(RONDA2, 283, '(\\"Caldas de Reis\\", \\"Curro\\", 2.85)', 250, 250)
print("## A2. Detección por el curador siguiente (informe):")
extracto(CURADOR, 503, "la transcripción de la AP-9 estaba desplazada", 120, 250)

print("## B. Curador con el prompt original de prompts/T2.4.md (primer mensaje):")
print(texto(lineas(CURADOR)[0])[:240], "\n")
print("## B1. Frase escrita en data/fuentes.md (tool_use):")
extracto(CURADOR, 480, "El Catálogo excluye los tramos transferidos (AP-68 vasco y navarro)", 120, 120)
print("## B2. Detección por revisor-spec:")
extracto(REVISOR, 228, "Afirmación falsa en `data/fuentes.md:49`", 20, 330)
print("## B3. Reconocimiento del curador:")
extracto(CURADOR, 622, "sí incluye el navarro", 120, 200)
