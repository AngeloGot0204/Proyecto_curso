# SDD — modelo-base-y-autenticacion

Backlog item #1 of "Generador de Reportes de Campo".

These files are an **export** of the Spec-Driven Development artifacts for this
change. The authoritative copies live in Engram (persistent memory); this folder
exists so the artifacts are readable, reviewable, and versioned in git.

If an artifact is updated in Engram, re-export it here — these files do not
update themselves.

## Contents

| File | Phase | Answers |
|---|---|---|
| [01-exploration.md](01-exploration.md) | `sdd-explore` | What exists today? What are the options? |
| [02-proposal.md](02-proposal.md) | `sdd-propose` | What are we building, why, and what is out of scope? |
| [03-spec.md](03-spec.md) | `sdd-spec` | What requirements and scenarios must hold? |
| [04-design.md](04-design.md) | `sdd-design` | How is it built technically? |
| [05-tasks.md](05-tasks.md) | `sdd-tasks` | In what ordered steps? |
| [06-decisions.md](06-decisions.md) | orchestrator | User-confirmed decisions taken during the session |
| [07-archive.md](07-archive.md) | `sdd-archive` | Final verification and archival state |

## Engram source of record

| Observation | Topic key |
|---|---|
| 35 | `sdd/modelo-base-y-autenticacion/explore` |
| 36 | `sdd/modelo-base-y-autenticacion/proposal` |
| 37 | `sdd/modelo-base-y-autenticacion/decisions` |
| 38 | `sdd/modelo-base-y-autenticacion/spec` |
| 39 | `sdd/modelo-base-y-autenticacion/design` |
| 40 | `sdd/modelo-base-y-autenticacion/tasks` |
| 41 | `sdd/modelo-base-y-autenticacion/delivery` |
| 42 | `sdd/modelo-base-y-autenticacion/django-version` |
| 43 | `sdd/modelo-base-y-autenticacion/apply-progress` |
| 44 | `sdd/modelo-base-y-autenticacion/verify-report` |
| 45 | `sdd/modelo-base-y-autenticacion/verify-remediation` |
| 47 | `sdd/modelo-base-y-autenticacion/archive-report` |
| 48 | `spec/usuarios` (living spec) |

## Dependency order

```
explore -> proposal -> spec ---> tasks -> apply -> verify -> archive
                        ^
                        |
                     design
```
