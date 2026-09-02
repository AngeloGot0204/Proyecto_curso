# Cierre: Move Report Closure From Revision To Participantes

**Estado: cerrado como ABANDONADO — 2026-09-01. Nada de este change se
mergeó a `openspec/specs/`.**

## Por qué se abandona

El change proponía mover el cierre del reporte (el `VistoBueno`) de la
pantalla de revisión (S-09) a la de participantes (S-10). Se archiva sin
aplicar porque **el código hace lo contrario**, verificado en disco:

| Afirmación del change | Realidad en el código |
|---|---|
| El formulario de cierre vive en `participantes.html` | `participantes.html` no tiene formulario de cierre |
| `revision.html` no crea `VistoBueno` | `revision.html:69` tiene el form a `reportes_cerrar` |
| El botón se oculta para no-creadores | Se usa el patrón `disabled`, no ocultamiento |
| Rama de inelegibilidad redirige a `reportes_participantes` | Redirige a `reportes_revision` |

Sus `tasks.md` tenían las fases 3 a 7 marcadas `[x]` sin respaldo en disco.
Esas marcas se corrigieron a `[ ]` antes de archivar.

Lo único de este change que sí aterrizó es la task 2.2: el redirect de éxito
de `cerrar_reporte` apunta a `reportes_mis`, y así sigue.

## Qué NO se mergeó

Los dos delta specs de `specs/` quedan marcados `STALE — NOT APPLIED` y
**no deben mergearse**: describen un sistema que no existe.

- `specs/cierre-reporte/spec.md`
- `specs/colaboracion-reporte/spec.md`

## Estado real, ya documentado en otro lado

La pantalla de revisión (S-09) es la dueña del cierre. Eso quedó reflejado en:

- `openspec/specs/cierre-reporte/spec.md` (sin cambios: ya era correcto)
- `BACKLOG.md` ítem #8
- `DESIGN.md` S-09 y S-10

## Si se quiere retomar

Abrir un change nuevo contra el código actual. Este no sirve como base: sus
referencias de línea y su lectura del estado inicial ya no aplican.
