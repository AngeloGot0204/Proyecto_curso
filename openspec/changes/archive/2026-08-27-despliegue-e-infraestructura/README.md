# SDD — despliegue-e-infraestructura (BACKLOG #2)

Ciclo SDD del ítem #2: despliegue en Vercel, base de datos en Neon,
almacenamiento en Vercel Blob, hardening HTTPS y manejo de secretos (ADR-0009).

## Fases

| Fase | Archivo |
|---|---|
| 1 · Explore | `exploration.md` |
| 2 · Propose | `proposal.md` |
| 3 · Spec | `specs/despliegue-e-infraestructura/spec.md` |
| 4 · Design | `design.md` |
| 5 · Tasks | `tasks.md` |
| 6 · Verify | `verify-partial.md` (parcial) y `verify-report.md` (final) |
| 7 · Archive | **nunca corrió — quedó bloqueada**, ver abajo |

`export-notes.md` es el README original del export y conserva el veredicto
completo del verify, la lista de WARNINGs y los IDs de observación de Engram.

## Por qué la fase Archive quedó bloqueada

El verify final dio **PASS WITH WARNINGS con 1 CRITICAL abierto**, y ese
CRITICAL impedía un archive limpio: la spec exigía servir los estáticos **sin**
WhiteNoise, y la implementación terminó usándolo (commit `356f8e6`) después de
dos fracasos empíricos del diseño original. El código, su test y el
comportamiento en producción eran consistentes entre sí — el documento stale
era la spec.

Ese CRITICAL **ya está resuelto**: la spec viva
(`openspec/specs/despliegue-e-infraestructura/spec.md`) exige WhiteNoise y
documenta la evidencia empírica que forzó el cambio. La spec archivada acá
conserva el texto viejo, que es el que el verify marcó como falsificado.

También quedó registrada una excepción aceptada por exceder el presupuesto de
revisión: 424 líneas contra un tope de 400.

## Nota sobre la spec archivada

`specs/despliegue-e-infraestructura/spec.md` es la spec **tal como se escribió
en su momento**. Su requirement "Vercel Blob provisioned but unconsumed"
prohibía explícitamente que el código consumiera el Blob store.

Eso cambió después: `config/storage.py` usa Vercel Blob como backend de
almacenamiento por defecto en producción. La spec viva y vigente es
`openspec/specs/despliegue-e-infraestructura/spec.md`. Este archivo se
conserva como registro histórico del ciclo, no como contrato.

Buena parte de sus escenarios son de verificación **manual** (live o consola
del proveedor) y no automatizables desde la suite — está señalado en la propia
spec con su leyenda de tipos de verificación.
