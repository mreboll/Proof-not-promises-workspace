# Registro de lecciones (fallos reales de la IA)

Una línea por fallo, apuntada en el momento. Es material directo para el pitch.

| Hora | Qué hizo mal la IA | Impacto | Capa del embudo que lo habría evitado |
|---|---|---|---|
| H0 | El scaffold asumía que los PR cambiaban la serialización binaria en ejecución, pero los 4 tocan el generador y el analizador | El oráculo diferencial habría medido algo que el PR nunca toca | T3: leer el diff real antes de elegir el oráculo |
| H1 | Nemotron 3.5 Super VL (rol `pro`), escribiendo el test de #2283 solo desde el issue, se inventó la API de Roslyn (`GeneratorDriver.Diagnostics`, `GeneratorDriver.GeneratedSources`) y olvidó `using Microsoft.CodeAnalysis.Diagnostics` para `WithAnalyzers`; en el reintento con el error del compilador repitió los mismos fallos | El test no compila ni en base ni en PR: sin evidencia, veredicto ROJO ("se niega a decidir") en vez de un falso verde | T1: un test solo cuenta si compila y es rojo en base y verde en PR; un fallo de compilación nunca cuenta como "reproduce el bug" |
| H1 | El scaffold resumía #2283 como "el analizador reporta diagnósticos sobre tipos de ensamblados referenciados" (`config.py` y `fixtures/triage_2283.json`). El issue real es un `IndexOutOfRangeException` en `TypeCollector` (`DeclaringSyntaxReferences[0]` sobre un struct genérico cerrado de otro ensamblado) | El triaje de alcance y el test independiente habrían juzgado el PR contra un requisito inventado | T3: el alcance se juzga contra el texto literal del issue (`issues/<id>.md`), nunca contra un resumen generado |
| H2 | Claude (Persona A) escribió la implementación de `dotnet.py` a la vez que sus tests, sin verlos fallar antes | Riesgo de tests que confirman el código en vez de especificarlo; los tests sí cubrían los caminos, pero no se vio el ROJO | T2: un test solo vale si se ha visto fallar |
