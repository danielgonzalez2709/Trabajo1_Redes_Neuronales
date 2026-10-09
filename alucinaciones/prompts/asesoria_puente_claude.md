# Prompts literales — asesoría de Claude al puente (Daniel)

- **Herramienta y modelo:** Claude Code (aplicación de escritorio), modelo Claude Opus 5.5 (`claude-opus-5-5`).
- **Sesión:** conversación de asesoría del puente, iniciada el 29-sep-2026.
- **Transcripción:** copia literal de los mensajes del usuario (incluidos errores de tipeo). Las rutas a archivos adjuntos se
  conservan tal como se escribieron.
- **Hallazgos que dependen de estos prompts:** H-01 (A), H-03 (B), H-06 (A, B, C), H-07 (B, C).

---

## Prompt A — 29-sep-2026 (primer mensaje de la sesión)

```text
@"C:\Users\danie\Downloads\Trabajo 1_ Optimización numérica, metaheurística y combinatoria.docx"
Necesito que me ayudes con mi primer trabajo de mi materia de Redes Neuronales y Algoritmos Bioinspirados, adjunto está el enunciado del trabajo, ten en cuenta que somos 5 integrantes en el grupo (contadome a mi). Ten pendiente el punto 5. Cacería de la alucinación 🎯. Necesito que hagas anotaciones de esto. Por ahora, no hagas nada, solo lee, dime de que trata y puedes darme un plan de trabajo para el equipo. Y haz un listado de MIS tareas individuales, las cosas que yo debo tener en cuenta como por ejemplo grabar el video del punto 4. La idea es que  yo sepa en todo momento el contexto de lo que sea que estemos haciendo, necesito que me expliques todo muy bien, podriamos hacer un archivo exclusivo para mi, como para tener un mejor contexto y entendimiento del problema
```

Respuesta: guía personal del puente (archivo local, no versionado) y resumen en el chat.

---

## Prompt B — 29-sep-2026 (pedido de soluciones para ambas partes)

```text
Bueno, acabo de tener una reunion con mi equipo y llegamos a la conclusion de devidirlo asi, Parte 1 se van a encargar 2 personas, la parte 2 otras dos personas, yo seré el puente, la idea es yo verificar que lo que desarrollen los dos equipos tenga sentido, buen contexto, y todos entendamos como funcionan completamente las soluciones. Yo creería que me voy a encargar de la integracíon y casería, el punto E que me propusiste de primero. 

Por ahora lo que acordamos es que ibamos a consultar las mejores opciones de solucion para cada Parte del trabajo, en sus respectivos equipos, yo tambien debo consultarlo, las dos partes, con criterio, y necesito que tu me ayudes en eso. Dame soluciones viables para cada parte con todos sus detalles, yo lo leo, evaluo, te consulto dudas si tengo alguna. 

La  idea es que para el proximo jueves despues de clase, tengamos ya las soluciones consultadas para empezar a desarrollar,  vamos a desarrollar con Subagent Driven Development, tendremos una reunion y vamos  a crear el Spec del proyecto, para que cada equipo lo desarrolle, con el contexto correcto, los datos correctos y todo el plan que se debe hacer para conseguir un desarrollo exitoso
```

Respuesta: `SOLUCIONES_PROPUESTAS.md` (archivo local del puente, no versionado; los extractos relevantes están citados en el registro).

---

## Prompt C — 1-oct-2026 (pedido del Spec)

```text
@"C:\Users\danie\Downloads\message.txt" @"C:\Users\danie\dev\Trabajo 1 Redes Neuronales/"
Los compañeros encargados de la parte 2 propusieron  esta solucion, me parece mucho mas especifica para la parte de la recoleccion de los datos de peaje, combustible, tipo de vehiculo. Haz los ajustes necesarios en la parte 2 y armemos de una vez el spec del trabajo, la idea es usar Subagent Driven Development, que tipo de agentes crees que sean necesarios para este trabajo a parte del orquestador, implementador y reviewer de calidad. Ponlo en la ruta de la carpeta de Trabajo 1 Redes Neuronales, si necesitas algo mas se libre en preguntarme
```

Respuesta: Spec v1.0, PLAN, `CLAUDE.md` y agentes (commit `2cd005b`).
