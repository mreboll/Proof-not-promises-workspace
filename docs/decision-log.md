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
| D10 | Los snapshots `Resources/**.g.cs` no pasan por el LLM de alcance: son IN si el issue habla del código generado | Preguntar al LLM fichero a fichero | En #2297 son 222 de 237 ficheros: casi todo el coste en tokens para una decisión que una regla toma igual |
| D11 | Las reglas de línea (`public`, `Span<`, `unsafe`) solo miran `src/**/*.cs`, sin comentarios ni literales | Buscar en todas las líneas del diff | Si no, los `public async Task` de los tests y el texto que emiten las plantillas `.tt` se tomarían por cambios de API |
| D12 | Huecos de la matriz por el lado prudente: sin evidencia → rojo (M3); riesgo alto sin interrogatorio → rojo (M7) | Aprobar por defecto si falta una etapa | La tesis es "sin pruebas no se aprueba": una etapa que no se ejecutó no puede contar como superada |
| D14 | Si el LLM de alcance no da JSON válido: reintento con el rol `pro` y, si vuelve a fallar, el fichero queda OUT con "revisión humana" | Abortar el triaje, o marcarlo IN por defecto | Un fallo del modelo no puede tumbar 237 ficheros, ni aprobar en silencio un fichero que nadie ha clasificado |
| D13 | El alcance se juzga contra el texto literal de `issues/<id>.md`, delimitado como datos no fiables | Usar el resumen de `config.py` | El resumen de #2283 estaba mal (lessons-log H1); y el texto del issue o del diff podría contener instrucciones para el modelo |
