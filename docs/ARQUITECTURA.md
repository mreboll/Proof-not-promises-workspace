# Tieto: "Risk-Scoped Evidence Ledger" (v2.1)

> Versión final de la idea para *Earned Trust in AI Code*. Combina tres capas en un embudo: **T3** (alcance y riesgo), **T1** (evidencia ejecutable) y **T2** (interrogatorio que solo produce tests).
> Respecto a la v2.0, la **v2.1** cierra cinco huecos que siguen abiertos. Están marcados con 🆕.

---

## 1. Tesis y principios

El reto de la ingeniería con IA no es escribir código, sino **que una persona asuma la responsabilidad de aprobar cambios enormes sin leerlos línea a línea**. Sustituimos la revisión manual exhaustiva por una **auditoría escalonada y determinista**, basada en tres principios:

1. **Riesgo proporcional y determinista (T3):** el nivel de escrutinio lo deciden **reglas estáticas auditables** (rutas, visibilidad `public`, namespaces críticos) y la trazabilidad al ID del requisito. Nunca la intuición de un LLM.
2. **Evidencia por encima de elocuencia (T1):** ninguna IA aprueba código con argumentos. La confianza nace **solo** de pruebas ejecutables: tests de regresión y testing diferencial binario.
3. **El desacuerdo solo produce pruebas (T2):** el Defensor nunca convence al Fiscal con palabras. Una objeción se cierra **únicamente** con un test nuevo que pasa. Si no, el sistema **se niega a decidir** y hace falta firma humana.

---

## 2. El pipeline en tres etapas

Todo informe empieza indicando el **ID del requisito** (por ejemplo, `Issue #2283`), el **tipo de cambio** (bug fix o feature) 🆕 y los commits comparados.

### Etapa 1: triaje de alcance y riesgo (T3, *Intent Diff*)

**Eje A: alineación de alcance** (LLM más trazabilidad al issue)
- *In-Scope:* responde directamente al requisito.
- *Out-of-Scope:* fichero o bloque que el ticket no pide.

**Eje B: riesgo por reglas estáticas** (sin LLM, 100 % auditable)
- **Bajo:** `/tests/`, `.md`, `.csproj`, `.editorconfig`, y cambios internos sin exposición externa.
- **Medio:** lógica `private` o `internal` en `src/`.
- **Alto:** firmas `public` o contratos de API, memoria (`Span<T>`, `unsafe`) y namespaces núcleo de serialización de MessagePack.

**Reglas de salida**

| Alcance | Riesgo | Resultado |
|---|---|---|
| Out-of-Scope | Alto | 🔴 Rojo directo |
| Out-of-Scope | **Medio** 🆕 | 🟡 Amarillo, con la justificación del agente y revisión del fragmento |
| Out-of-Scope | Bajo | 🟡 Amarillo, con la justificación del agente |
| In-Scope | Cualquiera | Pasa a la Etapa 2 |

### Etapa 2: verificación por evidencia ejecutable (T1, *Evidence Ledger*)

El sistema formula afirmaciones verificables y exige pruebas según el riesgo.

**Riesgo bajo:** compila sin errores y pasa la suite existente (`dotnet test`).

**Riesgo medio o alto: regla doble**
1. **Test del cambio,** según el tipo 🆕:
   - **Bug fix** (#2283, #2234): un test que reproduce el issue **falla en la rama base y pasa en la del PR**.
   - **Feature** (#2129, #2297): un test del comportamiento nuevo **pasa en la rama del PR**, y el comportamiento anterior se mantiene.
   - 🆕 **Independencia del test:** lo escribe **un agente que solo ve el texto del issue, no el diff**. Si el test lo escribe el mismo agente que hizo el fix, se valida a sí mismo y la prueba no vale nada.
2. **Invarianza binaria:**
   - **Dos apps de consola aisladas**, una compilada contra la rama base y otra contra la del PR, para evitar conflictos al cargar ensamblados en .NET.
   - Cada una serializa el mismo corpus a ficheros, y Python compara los SHA-256.
   - Fuera del caso del issue, los hashes tienen que ser **idénticos**.
   - 🆕 **Control de determinismo:** primero se ejecuta **dos veces la rama base** y se comprueba que sus hashes coinciden entre sí. Así sabemos que una diferencia la causa el PR y no un orden no determinista, por ejemplo en diccionarios.

**Reglas de salida**
- Falla el test del cambio o hay hashes distintos fuera del alcance del issue → 🔴 **Rojo**.
- Todo pasa y el riesgo es bajo o medio → 🟢 **Verde**, aprobado con evidencia.
- Todo pasa y el riesgo es alto → pasa a la Etapa 3.

### Etapa 3: interrogatorio que genera tests (T2, *Cross-Examination*)

Solo entran fragmentos In-Scope de riesgo alto que ya superaron la Etapa 2. Hay **un máximo de 3 preguntas**.

- **Fiscal:** busca casos límite no cubiertos (`null`, buffers vacíos, tipos anidados, concurrencia o compatibilidad hacia atrás).
- **Defensor:** **no puede contestar con texto.** Para cada objeción genera un test ejecutable y lo lanza con `dotnet test`.
- 🆕 **Antitrampa:** un test solo cuenta si **falla contra un mutante**, es decir, una versión del código con el caso límite roto a propósito. Así se descartan tests vacíos como `Assert.True(true)`, que aprobarían cualquier cosa.

**Reglas de salida**
- Todas las objeciones cubiertas por tests válidos, y el cambio **no** toca una firma `public` → 🟢 **Verde**.
- Todas cubiertas, pero **sí** toca una firma `public` → 🟡 **Amarillo final**. El humano solo valida el diseño de la API, sabiendo que el comportamiento está probado.
- Alguna objeción sin test válido tras 3 rondas → 🔴 **Rojo, "el sistema se niega a decidir"**, y se adjunta la pregunta exacta del Fiscal.

---

## 3. Matriz final y firma humana

| Estado | Criterio | Qué ve el humano | Acción |
|---|---|---|---|
| 🟢 **Verde** | In-Scope, riesgo bajo o medio, pruebas superadas (u objeciones del Fiscal convertidas en tests válidos) | Resumen de las afirmaciones y los hashes | **No lee el código**; la evidencia respalda la aprobación |
| 🟡 **Amarillo** | (A) Out-of-Scope de riesgo bajo o medio con justificación, **o** (B) riesgo alto que superó el interrogatorio pero toca una firma `public` | Solo la firma pública o el fichero justificado | **Revisión rápida y focalizada** |
| 🔴 **Rojo** | Out-of-Scope de riesgo alto, fallo diferencial, o negativa a decidir | Las líneas exactas más la objeción sin resolver | **Auditoría manual obligatoria** de esas líneas |

**Bloque de firma (rendición de cuentas)**
```text
--- REGISTRO DE APROBACIÓN Y RENDICIÓN DE CUENTAS ---
Requisito / Issue ID: #2283 (bug fix) | Rama evaluada: ju26-issue-2283 | Base: <commit>
Afirmaciones auto-verificadas (Verde): [X/Y] | Revisadas manualmente (Amarillo/Rojo): [Z/Y]
Aprobado por (nombre y apellidos): ______________________  Rol: _________________
Timestamp (UTC): ____________________ | Decisión: [ ] APROBADO  [ ] RECHAZADO
```

---

## 4. Plan de ejecución (12–14 h)

**Paso 0 (horas 0–2, crítico):** clonar el repositorio, instalar el SDK de .NET que indique `global.json` y comprobar que `dotnet test` funciona **antes de escribir nada en Python**. Si no compila en 2 h, se reduce el alcance a #2283.

**Bloque técnico (horas 2–9, Informática).** Un orquestador en Python que:
1. Lee el `git diff` y clasifica cada fichero con las reglas estáticas.
2. Genera el test del cambio con un agente que solo ve el issue, y lo ejecuta en las dos ramas.
3. Lanza las dos apps de consola, comprueba el determinismo y compara los SHA-256.
4. Ejecuta el bucle de 3 preguntas, en el que el Fiscal objeta, el Defensor genera un test, se ejecuta `dotnet test` y se pasa la comprobación con el mutante.
5. Genera el informe en **Markdown o HTML estático** con el ID del requisito, los resultados reales y el bloque de firma.
6. **Escalabilidad:** pasa la Etapa 1 sobre el PR de 237 ficheros y publica **los números reales** que salgan.

**Bloque de negocio (horas 2–12, ADE)**
1. **Concept Card** (1–2 páginas): principios, matriz de riesgo, trade-offs (coste de compilación y tokens frente a las horas de revisión que se ahorran) y **límites**:
   - No detecta errores de producto si el ticket estaba mal escrito.
   - No sirve en zonas sin un oráculo diferencial.
2. **Registro de decisiones:** reglas estáticas en lugar de LLM, 3 preguntas, dos procesos aislados, tests escritos solo a partir del issue y comprobación con mutantes.
3. **Registro de lecciones:** fallos reales de la IA durante el hackathon (en AstraZeneca, Aalto y este reto), cada uno ligado a la capa del embudo que lo habría evitado.

---

## 5. Guiones

**Vídeo (2:00 como máximo, estricto)**
- **0:00–0:30 El problema:** un agente toca cientos de ficheros, pero firma un humano. Leerlo todo es inviable, y fiarse del resumen de la IA es negligente.
- **0:30–1:10 El embudo T3 → T1 → T2:** reglas estáticas, dos binarios aislados y un Fiscal que obliga a escribir tests.
- **1:10–1:45 Demo sobre #2283:** el test falla en la base y pasa en el PR, los hashes son idénticos, una objeción se convierte en test y queda un bloqueo en rojo con su firma. Después, los números reales del PR de 237 ficheros.
- **1:45–2:00 Honestidad:** la Concept Card, el registro de decisiones y los límites.

**Pitch en directo (3:00):** la misma estructura, y el minuto extra se dedica al intercambio entre Fiscal y Defensor y a dos casos reales del registro de lecciones.
