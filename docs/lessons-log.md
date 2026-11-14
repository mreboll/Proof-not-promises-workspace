# Registro de lecciones (fallos reales de la IA)

Una línea por fallo, apuntada en el momento. Es material directo para el pitch.

| Hora | Qué hizo mal la IA | Impacto | Capa del embudo que lo habría evitado |
|---|---|---|---|
| H0 | El scaffold asumía que los PR cambiaban la serialización binaria en ejecución, pero los 4 tocan el generador y el analizador | El oráculo diferencial habría medido algo que el PR nunca toca | T3: leer el diff real antes de elegir el oráculo |
| H1 | Nemotron 3.5 Super VL (rol `pro`), escribiendo el test de #2283 solo desde el issue, se inventó la API de Roslyn (`GeneratorDriver.Diagnostics`, `GeneratorDriver.GeneratedSources`) y olvidó `using Microsoft.CodeAnalysis.Diagnostics` para `WithAnalyzers`; en el reintento con el error del compilador repitió los mismos fallos | El test no compila ni en base ni en PR: sin evidencia, veredicto ROJO ("se niega a decidir") en vez de un falso verde | T1: un test solo cuenta si compila y es rojo en base y verde en PR; un fallo de compilación nunca cuenta como "reproduce el bug" |
