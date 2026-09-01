# SDD -- despliegue-e-infraestructura

Backlog item #2 of "Generador de Reportes de Campo".

These files are an export of the Spec-Driven Development artifacts for this
change. The authoritative copies live in Engram (persistent memory); this
folder exists so the artifacts are readable, reviewable, and versioned in
git.

If an artifact is updated in Engram, re-export it here -- these files do not
update themselves.

This change is at the full verify phase. Verdict: **PASS WITH WARNINGS -- 1
CRITICAL open, blocking a clean archive.** See
[07-verify.md](07-verify.md) and Engram
`sdd/despliegue-e-infraestructura/verify-report` (observation 67).

> **Full verify complete (2026-08-27).** All 26 spec scenarios attempted:
> 14/14 Automatable pass at runtime, 6/6 Manual-console PASS, 6/6 Manual-live
> PASS or PASS-with-note (ML-5, ML-6 carry one live sub-case each not
> independently re-verified, both backed by passing automated tests).
> Independently re-run this session (not only user-attested): full pytest
> suite (35 passed), `manage.py check` (clean), and 4 live `curl` checks
> against the deployed Production URL (HTTPS reachability, static asset
> serving, HSTS/cookie headers, `/admin/` gating).
>
> **1 CRITICAL open**: `03-spec.md`'s "Static file serving without
> WhiteNoise" requirement is now falsified by the implementation. Two
> empirical failures of the original design (Vercel auto-entrypoint
> detection, then Vercel auto-serving `collectstatic` output) forced a pivot
> to WhiteNoise (commit `356f8e6`), which directly contradicts the spec's
> literal "no WhiteNoise" text and its "served by Vercel CDN not a 404"
> live scenario. The code, its test, and the live behavior are all
> internally consistent and correct -- only the spec document is stale.
> **Must be resolved (spec revision 3, or an explicit accepted exception like
> the budget one) before `sdd-archive` runs.**
>
> **5 WARNINGs**, none blocking on their own: (1) `05-tasks.md` checkboxes
> for Phases 1, 7, 8, 9, 10 remain unchecked despite the underlying work
> being done this session -- should be updated before archive; (2) the
> entrypoint-detection design divergence (`pyproject.toml`
> `[tool.vercel]`/`[project]`) is undocumented in the design record; (3)
> `pyproject.toml`/`requirements.txt` now duplicate dependencies by hand;
> (4) ML-5/ML-6 partial live coverage, both backed by automated tests; (5)
> the 424-line budget overrun remains an open accepted exception (Engram
> #56, restated, not reopened).
>
> The earlier CRITICAL from the partial verify (tasks 7.2/7.3 missing
> `DJANGO_SECRET_KEY`/`DATABASE_URL`) is **confirmed resolved** in the
> current `05-tasks.md`.

> **Partial verify (superseded) -- code half only (2026-08-26).** See
> [06-verify-partial.md](06-verify-partial.md) and Engram
> `sdd/despliegue-e-infraestructura/verify-report-partial` (observation 58).
> Kept for historical record; the full verify above supersedes its scope.

> **Apply -- code half done in commit `12ed1a5`** (424 insertions, 1
> deletion, not pushed at the time), plus 6 additional commits this session
> completing the infrastructure/deployment half: `c291fe1`, `6a62efd`,
> `976f8bc`, `26f3505`, `356f8e6`, `9c5bf85`. See [05-tasks.md](05-tasks.md)
> and Engram #57.

> **Budget overrun -- accepted as exception, not re-opened.** The tasks
> forecast said ~315 authored lines and single-commit delivery was chosen on
> that premise; the actual code-half change is **424 insertions**, over the
> 400-line review budget. Accepted as `size:exception` per Engram #56 --
> not reported as delivered within budget.

> **Spec amendment applied (revision 2).** `03-spec.md` and Engram #52 were
> revised to absorb design revision 2's Decision 11 (the four `check
> --deploy` transport warnings, resolved via `DJANGO_HTTPS_ONLY`). The spec
> states **12 requirements / 26 scenarios** (Automatable 14, Manual-live 6,
> Manual-console 6). **A revision 3 amendment is now recommended** (see the
> full verify's CRITICAL finding above) to align the static-file-serving
> requirement with the WhiteNoise implementation.

## Contents

| File | Phase | Answers |
|---|---|---|
| [01-exploration.md](01-exploration.md) | `sdd-explore` | What exists today? What are the options? |
| [02-proposal.md](02-proposal.md) | `sdd-propose` | What are we building, why, and what is out of scope? |
| [03-spec.md](03-spec.md) | `sdd-spec` | What requirements and scenarios must hold? |
| [04-design.md](04-design.md) | `sdd-design` | How is it built technically? |
| [05-tasks.md](05-tasks.md) | `sdd-tasks` | In what ordered steps? |
| [06-verify-partial.md](06-verify-partial.md) | `sdd-verify` (partial, superseded) | Does the code half hold up? RED re-derived, not assumed. |
| [07-verify.md](07-verify.md) | `sdd-verify` (full) | Full 26-scenario compliance matrix, live re-checks, both design divergences documented. |
| 08-archive.md *(pending -- blocked on resolving the CRITICAL above)* | `sdd-archive` | Final verification and archival state |

## Engram source of record

| Observation | Topic key |
|---|---|
| 49 | `sdd/despliegue-e-infraestructura/explore` |
| 50 | `sdd/despliegue-e-infraestructura/decisions` |
| 51 | `sdd/despliegue-e-infraestructura/proposal` |
| 52 | `sdd/despliegue-e-infraestructura/spec` |
| 53 | `sdd/despliegue-e-infraestructura/design` |
| 55 | `sdd/despliegue-e-infraestructura/tasks` |
| 56 | `sdd/despliegue-e-infraestructura/delivery` |
| 57 | `sdd/despliegue-e-infraestructura/apply-progress` |
| 58 | `sdd/despliegue-e-infraestructura/verify-report-partial` |
| 67 | `sdd/despliegue-e-infraestructura/verify-report` |

## Dependency order

```
explore -> proposal -> spec ---> tasks -> apply -> verify (partial) -> verify (full) -> [spec revision 3 or exception] -> archive
                        ^
                        |
                     design
```
