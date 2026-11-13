# Registro de decisiones

| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| D1 | El riesgo se decide con reglas estáticas | Que lo decida un LLM | Auditable y reproducible: el mismo diff da siempre el mismo riesgo |
| D2 | Invarianza de **generación** (código generado + diagnósticos) | Comparar bytes serializados en ejecución | Los 4 PR solo tocan el generador y el analizador |
| D3 | Base y PR en worktrees y procesos separados | Cargar las dos versiones en un mismo proceso | Evita conflictos al cargar ensamblados en .NET |
| D4 | El test del cambio lo escribe un agente que solo ve el issue | Que lo escriba el mismo agente que hizo el fix | Un agente que se valida a sí mismo no aporta evidencia |
| D5 | Un test solo cuenta si falla contra un mutante | Aceptar cualquier test que pase | Descarta tests vacíos como `Assert.True(true)` |
| D6 | Gemini, con temperature 0 y caché en disco | Llamadas sin caché | Demo repetible y protegida ante los 429 |
| D7 | Fiscal con **Nemotron** y Defensor y tests con **Gemini** | El mismo modelo en los dos papeles | Si acusación y defensa comparten modelo, comparten puntos ciegos; la diversidad reduce los errores correlacionados |
| D8 | Los tests generados por IA se ejecutan en **Modal Sandboxes sin red** | Ejecutarlos en el portátil | Son código no fiable: aislarlos es coherente con la tesis, y además permite paralelizar base, PR y mutantes |
| D9 | CI en **CRACI** | GitHub Actions estándar | Aplicamos la misma regla a nuestras dependencias: cada build deja registro verificable |
