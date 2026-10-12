# Asesoría del orquestador sobre el vehículo (T2.7) — conversación literal

- Fecha: 2026-10-11
- Herramienta: Claude Code (sesión principal / orquestador)
- Modelo: claude-opus-5-5
- Usuario: Jose Miguel

---

## Prompt del usuario (literal)

```text
ve haciendo commit de los cambios que hemos hecho. Ahora discutamos el siguiente punto, sobre el toyota

- Que era como tal la fase extra alta y km77 que mencionadaba la spec? explicamelo de forma sencilla
- No pudiste encontrar la ficha tecnica del modelo 2026?
- la elección del style plus y la información encontrada nos permite cubrir la descripcion del punto y la rubrica?
```

## Fragmento relevante de la respuesta de la IA (literal)

```text
**Una trampa con el "máximo 4,8":** no lo usemos como consumo de autopista. Es el WLTP del **mismo** ciclo con la versión
más equipada (llantas más grandes, extras). Para la sensibilidad de autopista conviene un parámetro de consumo
modificable desde la configuración, declarado como supuesto.
```

Con esa explicación, el orquestador redactó en el Spec v1.7, §7.2 Bloque 5:
"El "máximo" WLTP de 4,8 l/100 km **no** es la fase de autopista: es el combinado de la configuración más equipada, y no se usa como tal."

Ver H-12 en `alucinaciones/registro.md`.
