# SDD — modelo-base-y-autenticacion (BACKLOG #1)

Ciclo SDD del ítem #1: modelo `Usuario`, invariante `rol`/`is_staff`,
autenticación por sesión y las pantallas de administración de usuarios (S-13).

## Fases

| Fase | Archivo |
|---|---|
| 1 · Explore | `exploration.md` |
| 2 · Propose | `proposal.md` |
| 3 · Spec | `specs/usuarios-y-autenticacion/spec.md` |
| 4 · Design | `design.md` + `decisions.md` |
| 5 · Tasks | `tasks.md` |
| 6 · Verify | — no se produjo un `verify-report.md` por separado; la verificación quedó registrada en `archive-report.md` |
| 7 · Archive | `archive-report.md` |

`export-notes.md` es el README original del export y conserva los IDs de
observación de Engram de cada artefacto.

## Nota sobre la spec archivada

`specs/usuarios-y-autenticacion/spec.md` es la spec **tal como se escribió en
su momento**. Declara en Out of Scope que S-13 se resolvería con el admin de
Django y no con pantallas propias.

La capacidad terminó implementándose con pantallas propias en `/usuarios/`.
La spec viva y vigente es `openspec/specs/usuarios-y-autenticacion/spec.md`,
que describe el sistema actual. Este archivo se conserva como registro
histórico del ciclo, no como contrato.
