# SDD — motor-definicion-tipo-reporte (BACKLOG #3)

Ciclo SDD del ítem #3: modelos `TipoDeReporte`/`DefinicionDeTipo`, carga
declarativa YAML→JSONField y el validador exhaustivo de activación
(ADR-0003, ADR-0008).

## Fases

| Fase | Archivo |
|---|---|
| 1 · Explore | **falta** — no se produjo |
| 2 · Propose | **falta** — no se produjo |
| 3 · Spec | `specs/motor-definicion-tipo-reporte/spec.md` |
| 4 · Design | `design.md` |
| 5 · Tasks | `tasks.md` |
| 6 · Verify | `verify-report.md` (con `apply-progress.md` de la fase 5·Apply) |
| 7 · Archive | **falta** — no se produjo |

## Huecos del ciclo

Este ítem arrancó directamente en la fase Spec: no tiene exploración ni
proposal. La spec archivada se refiere a un "proposal (observation #72)" que
vivía en Engram y nunca se exportó a archivo, así que ese eslabón no es
recuperable desde el repositorio.

Tampoco tuvo fase Archive formal.

## Nota sobre la spec archivada

`specs/motor-definicion-tipo-reporte/spec.md` es la spec **tal como se
escribió en su momento**, en formato condensado — su propio encabezado avisa
que el texto verbatim de cada escenario quedó en Engram y que esto es una
condensación verificada durante `sdd-verify`.

Declara además en Out of Scope tanto la UI de administración propia (que
después se construyó, ítem #13) como el almacenamiento en Vercel Blob (que
después se adoptó). La spec viva y vigente es
`openspec/specs/motor-definicion-tipo-reporte/spec.md`, con los escenarios
Given/When/Then completos y alineada al código actual. Este archivo se
conserva como registro histórico del ciclo, no como contrato.
