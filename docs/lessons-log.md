# Registro de lecciones (fallos reales de la IA)

Una línea por fallo, apuntada en el momento. Es material directo para el pitch.

| Hora | Qué hizo mal la IA | Impacto | Capa del embudo que lo habría evitado |
|---|---|---|---|
| H0 | El scaffold asumía que los PR cambiaban la serialización binaria en ejecución, pero los 4 tocan el generador y el analizador | El oráculo diferencial habría medido algo que el PR nunca toca | T3: leer el diff real antes de elegir el oráculo |
