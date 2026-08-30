# Verify Report: adjuntos

## Change
adjuntos (backlog #11). Delivered as 4 chained PRs stacked-to-main (feat(reportes): Adjunto model -> feat(reportes): validacion+endpoint -> feat(reportes): pipeline cliente+cola offline -> feat(tipos_reporte): incrusta adjuntos en Excel), plus 3 follow-up bugfix commits found during manual verification (SECCION_DE_ADJUNTOS correction, broken multi-line Django comments, missing defer on adjuntos.js) and 1 additional bugfix (service worker CACHE bump). All 8 commits confirmed present on main via git log.

## Mode
Full artifact set (proposal, design, both specs -- one full spec, one delta -- and tasks). Full verification performed: completeness, correctness, coherence, plus real test execution.

## Task Completeness

| Phase | Status |
|---|---|
| 1. Foundation -- Adjunto Model and Migration (D1) | All 5 tasks checked. Migration is a single additive CreateModel, matches design D1 field-for-field |
| 2. Server Validation Module (D7, TDD) | All 5 tasks checked. reportes/adjuntos.py is pure, no DB access, matches design interface exactly |
| 3. Upload and List Endpoint (D2, TDD) | All 12 tasks checked. subir_adjunto/adjuntos_de_reporte match design's Interfaces/Contracts table verbatim |
| 4. Client Pipeline and Offline Queue (D3, D4) | All 6 tasks checked. offline-db.js version(3), adjuntos.js pipeline, own dedicated fetch, no second Dexie instance |
| 5. Excel Embedding and Anchor Validation (D5, D6, TDD) | All 12 tasks checked. _incrustar_adjuntos/R7 match design exactly, all 4 delta scenarios plus the undecodable-file threat-matrix test are covered |
| 6. Manual DevTools Verification | 6.1 unchecked with an honest, documented partial-verification caveat -- no real iPhone HEIC sample was available; the conversion/compression-failure fallback branch of the same task WAS exercised end-to-end (201, chip "Adjunto subido"). 6.2-6.5 checked, verified live against the dev server |
| 7. Cleanup / Documentation | All 4 tasks checked. 7.4 claims 327/327 passed -- independently re-confirmed below |

Unchecked task: 6.1 (real iPhone HEIC file conversion). Per the "any unchecked task blocks full verification" rule this is flagged below; it does not undermine the rest of the change since it is isolated to one client-side conversion-success path with a fully-proven fallback, and the gap is explicit rather than silently claimed as done.

## Test Execution Evidence

Ran the exact declared command myself, in isolation (single process, real Neon Postgres test DB), not trusted from tasks.md 7.4's claim:

```
.venv\Scripts\python.exe -m pytest -q
```

Result: 327 passed, 0 failed, exit 0, 694.94s (11m34s).

This independently confirms tasks.md 7.4's "327/327 passed (692s)" claim almost exactly (694.94s vs. the claimed 692s -- same order, negligible variance, consistent with re-running on a live remote DB). Zero regressions found across the full suite (reportes/, tipos_reporte/, and every other app).

Focused adjuntos-only counts (from source, cross-checked against the full run):
- reportes/tests/test_adjuntos.py: 13 test functions (2 parametrized, x5 and x2 cases -> 17 collected test items), covering Phases 1-3.
- tipos_reporte/tests/test_generador.py: 4 new attachment-embedding tests (Phase 5, D5).
- tipos_reporte/tests/test_validacion_plantilla.py: 5 new R7 tests (Phase 5, D6).

## Spec Compliance Matrix

Correction to the verification brief: adjuntos-reporte/spec.md currently has 9 requirements / 12 scenarios (confirmed by direct grep of "### Requirement:" / "#### Scenario:" markers), not 17 scenarios as stated in the task brief. generacion-reporte-excel/spec.md has 1 requirement / 4 scenarios, matching the brief. Combined: 10 requirements / 16 scenarios -- counted from the actual retrieved files, not assumed.

### adjuntos-reporte (9 requirements, 12 scenarios)

| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Standalone Adjunto Model | Attachment is stored independent of ValorDeReporte | test_adjuntos.py::test_adjunto_se_guarda_independiente_de_valorreporte | COMPLIANT |
| Format Allowlist | Server rejects a disallowed format independent of client validation | test_adjuntos.py::test_rechaza_formato_no_permitido (unit) + test_subir_adjunto_formato_no_permitido_devuelve_400_sin_crear_fila (integration) | COMPLIANT |
| Server-Side Size Ceiling | Oversized file rejected after failed/skipped client compression | test_adjuntos.py::test_rechaza_tamano_excedido_8mb_mas_1 (boundary) + test_subir_adjunto_tamano_excedido_devuelve_400_sin_crear_fila | COMPLIANT |
| Per-Attachment Failure Isolation | One invalid attachment does not block step submission | test_adjuntos.py::test_aislamiento_un_adjunto_invalido_no_bloquea_paso -- two-request test proving the step's 302 and field values are independent of the attachment's 400 | COMPLIANT |
| Client-Side HEIC Conversion Before Compression | HEIC file is converted then compressed | No automated JS runner (documented project-wide limitation). Task 6.1: partially verified with a simulated HEIC file -- detection and heic2any invocation confirmed; genuine device-output conversion NOT verified | PARTIAL (manual, honest gap) |
| Client-Side HEIC Conversion Before Compression | Non-HEIC file skips conversion | No dedicated manual step, but every non-HEIC upload exercised throughout Phase 6 (JPEG/PNG) never triggered heic2any per the esHeic() guard structure in adjuntos.js (source-verified: conversion call is unconditionally gated behind esHeic(archivo)) | COMPLIANT (source inspection + incidental live exercise) |
| Client-Side Best-Effort Compression with Fallback | CDN unreachable falls back to original file | Task 6.2, verified live (delete window.heic2any; delete window.imageCompression; then upload, 201 without compression) | COMPLIANT (manual) |
| Client-Side Best-Effort Compression with Fallback | Conversion or compression failure falls back to original file | Task 6.1's secondary path, verified live end-to-end (201, "Adjunto subido") | COMPLIANT (manual) |
| Client-Side Best-Effort Compression with Fallback | Fallback original still exceeds ceiling | Task 6.5, verified live (9MB fake attachment -> "Archivo demasiado grande (>8MB)") | COMPLIANT (manual) |
| Offline Queueing Through Shared Dexie Schema | Attachment queued and synced independently of step submission | Task 6.3, verified live (offline capture -> adjuntos_pendientes row -> reconnect -> Reintentar -> syncs and clears); server half by test_subir_adjunto_happy_path_crea_adjunto; dedicated-endpoint mechanism confirmed by source (adjuntos.js's own fetch to urlSubida, never form.action) | COMPLIANT (matches the corrected, current scenario text) |
| No Hard Cap on Attachment Count | Multiple attachments accepted for one report | test_adjuntos.py::test_multiples_adjuntos_sin_limite_de_cantidad (5 sequential uploads, all 201) | COMPLIANT |
| Server-Side Listing and Download | Authorized user lists a report's attachments | test_adjuntos.py::test_lista_adjuntos_autorizado_incluye_metadata_y_enlace | COMPLIANT |

Compliance summary: 11/12 scenarios fully compliant, 1/12 partial (HEIC genuine-device conversion, honestly caveated, not silently claimed).

### generacion-reporte-excel delta (1 requirement, 4 scenarios)

| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Attachment Embedding via Anchor Slots | Attachments within anchor-slot count are embedded | test_generador.py::test_adjuntos_dentro_del_limite_de_anclas_se_incrustan -- asserts len(hoja._images) == 3 AND exact (col, row) anchor coordinates for all 3 | COMPLIANT |
| Attachment Embedding via Anchor Slots | Attachments beyond anchor-slot count remain stored, not embedded | test_generador.py::test_adjuntos_mas_alla_del_limite_de_anclas_quedan_almacenados_no_incrustados -- 6 attachments, 4 slots, len(hoja._images) == 4, no exception | COMPLIANT |
| Attachment Embedding via Anchor Slots | No attachments leaves anchor slots empty | test_generador.py::test_sin_adjuntos_deja_las_anclas_vacias | COMPLIANT |
| Attachment Embedding via Anchor Slots | Template without declared anchor slots skips embedding entirely | test_generador.py::test_plantilla_sin_anclas_declaradas_no_incrusta_nada -- attachments present but no adjuntos key, hoja._images == [] | COMPLIANT |

Compliance summary: 4/4 scenarios compliant.

## Correctness (Static Evidence)

| Area | Status | Notes |
|---|---|---|
| reportes/models.py::Adjunto | Implemented | Exact D1 field set, FileField (not ImageField, correct rationale re: HEIC/Pillow), Meta.ordering = ("fecha_subida", "id") |
| reportes/migrations/0006_adjunto.py | Implemented | Single additive CreateModel, correct FK on_delete (CASCADE for reporte, PROTECT for autor), matches model exactly |
| reportes/adjuntos.py | Implemented | Pure validar_adjunto, no DB access, format checked before size (documented as non-semantic ordering), SECCION_DE_ADJUNTOS = "resultados" -- matches the corrected fix commit |
| reportes/views.py::subir_adjunto | Implemented | validar_adjunto runs before any Adjunto.objects.create, seccion_id never trusted from client, JsonResponse error ids match design's contract table exactly |
| reportes/views.py::adjuntos_de_reporte | Implemented | _reporte_accesible-scoped, renders required metadata fields |
| reportes/views.py::generar | Implemented | Passes adjuntos=[a.archivo for a in reporte.adjuntos.all()], dependency direction preserved (tipos_reporte never imports reportes) |
| reportes/static/reportes/offline-db.js | Implemented | version(3) appended after the existing version(2) block verbatim, single .version() owner preserved, window.reportesOfflineDB global correctly consumed by adjuntos.js |
| reportes/static/reportes/adjuntos.js | Implemented | Both CDN libs feature-detected (typeof ... === "function"), own dedicated fetch, per-attachment chip/retry UI, reconciliar() re-renders without auto-retry (ADR-0004/S-15 consistent) |
| reportes/templates/reportes/paso.html | Implemented, bug-fixed | {% comment %}{% endcomment %} used correctly for both multi-line comments (the original {# #} bug is gone); adjuntos.js script tag has defer (the original missing-defer bug is fixed); gated on seccion.id == "resultados", consistent with the corrected SECCION_DE_ADJUNTOS |
| reportes/templates/reportes/sw.js | Implemented, bug-fixed | CACHE = "reportes-offline-v2" (bumped from v1), confirmed by git show 21a3afd |
| tipos_reporte/generador.py::_incrustar_adjuntos/_encajar | Implemented | String-anchor form (hoja.add_image(img, slot["celda"])), correctly distinct mechanism from _intercambiar_logo's anchor-object copy; zip() truncation enforces the 4-slot cap; decode failures caught via try/except Exception: logger.exception(...); continue, never raised |
| tipos_reporte/validacion.py::_validar_anclas_de_adjuntos (R7) | Implemented | Reuses _es_celda_valida, does NOT call R6's merged-anchor rule or _validar_colisiones_de_celda, matching D6's explicit non-application |

### Other script tags / multi-line comment sweep (repo-wide)

Per the task brief's specific concern -- whether the missing-defer / broken-multi-line-comment bugs recur elsewhere -- swept every <script> tag and every {# ... #} Django comment across the project's own templates (excluding .venv's vendored Django admin templates, which are framework code, not project code).

- Only reportes/templates/reportes/paso.html uses <script> tags among this project's own templates. All 7 script tags inspected: dexie.js (no defer, intentional -- same pre-existing pattern the Dexie CDN tag has always used, since offline-db.js/paso-offline.js's DB setup does not depend on DOM readiness), paso.js/paso-offline.js/adjuntos.js (all correctly deferred -- DOM-manipulating scripts), offline-db.js (no defer, same DB-setup rationale as Dexie, pre-existing pattern unrelated to this change), heic2any/browser-image-compression (CDN libs, no defer needed -- they only expose globals, consumed later by the deferred adjuntos.js). No other missing-defer bug found.
- Only Django's own vendored admin templates (.venv/Lib/site-packages/django/contrib/admin/...) use single-line {# #} comments; zero occurrences in this project's own template code. The multi-line {# #} bug that was fixed here does not recur anywhere else in the codebase.

## Design Coherence (D1-D7)

| Decision | Implemented as designed |
|---|---|
| D1, Adjunto is a FileField, not ImageField | Yes, exact field set and rationale match |
| D2, separate endpoint, not the step's FormData POST | Yes -- adjuntos.js issues its own fetch to /reportes/<id>/adjuntos/subir/; confirmed the spec's "Offline Queueing" scenario text now matches this mechanism exactly (Open Question 1, resolved) |
| D3, client pipeline in its own file, both CDN libs optional | Yes -- adjuntos.js created standalone, typeof ... === "function" feature detection throughout, no hard dependency on either library |
| D4, offline-db.js version(3), new adjuntos_pendientes store | Yes -- single .version() owner preserved, no second Dexie(...) instance introduced |
| D5, _incrustar_adjuntos: coordinate-string anchors, injected files | Yes -- string-anchor form used (not the object-copy mechanism), adjuntos=() keyword injected rather than queried inside tipos_reporte, dependency direction preserved |
| D6, anchor slots get notation validation, not merged-anchor validation | Yes -- R7 does not call R6's merged-anchor rule or _validar_colisiones_de_celda, confirmed by dedicated negative test |
| D7, server validation is a pure module, shared by view and tests | Yes -- reportes/adjuntos.py::validar_adjunto is pure, no DB access, called by both subir_adjunto and its own unit tests |

Open Questions (design.md):
- [x] Offline Queueing mechanism -- resolved, spec text now matches D2 exactly (confirmed above).
- [x] SECCION_DE_ADJUNTOS real section id -- resolved via the f79ea1d fix commit ("s-08-croquis-evidencia" -> "resultados"), verified against reportes/adjuntos.py, paso.html's two {% if seccion.id == "resultados" %} gates, and the seccion_s08_id test fixture, all consistently updated. Verified live per task 6.x.
- [ ] Anchor-slot box defaults (320x240px) -- deliberately deferred by user decision to be configured later via Django admin once estructura["adjuntos"] gets a real slot list. _incrustar_adjuntos correctly no-ops with zero declared slots in the meantime (confirmed by test_plantilla_sin_anclas_declaradas_no_incrusta_nada and test_sin_adjuntos_declarados_no_reporta_problemas_de_r7). This is a genuine, documented, non-blocking deferral, not a defect -- treated as informational, not counted as an issue.
- [x] CDN pinning/SRI -- resolved, matches the existing no-integrity Dexie precedent.

No undocumented design deviations found.

## Issues Found

CRITICAL: None.

WARNING
1. Task 6.1 ("Client-Side HEIC Conversion Before Compression", "HEIC file is converted then compressed" scenario) remains genuinely unverified against real device output -- tasks.md is explicit and honest about this (unchecked, with the caveat spelled out), so it is not a hidden gap, but the spec's primary HEIC-conversion-success scenario has no passing covering test, automated or manual-with-real-hardware. The closely-related fallback scenario (conversion failure -> original file) IS fully proven end-to-end. Recommend running this specific check against a real iPhone-captured HEIC file before treating the HEIC pipeline as fully proven, though it does not block server-side correctness (the server independently re-validates any format that does arrive, per D7 defense-in-depth).
2. proposal.md's Success Criteria checklist (6 items) remains all-unchecked even though the change is fully delivered, tested, and (mostly) manually verified -- artifact hygiene, not a functional gap.

SUGGESTION
1. tasks.md 1.5's resolution note still literally says the seccion_s08_id fixture value is "s-08-croquis-evidencia" -- stale text left over from before the f79ea1d fix; the actual fixture (reportes/tests/conftest.py) and reportes/adjuntos.py::SECCION_DE_ADJUNTOS both correctly read "resultados" today, and tasks.md 7.1 does correctly document the fix. Purely a documentation-consistency nit inside 1.5's own note, not a code defect -- consider updating 1.5's wording for future readers.
2. Once a real iPhone HEIC sample becomes available, add it to the manual DevTools checklist and check off 6.1 fully, closing the one remaining WARNING.

## Verdict

PASS WITH WARNINGS

Server-side (Python/Postgres/openpyxl) requirements are implemented exactly as designed across all 7 design decisions (D1-D7) and are fully proven by 327 passing tests with zero regressions (independently re-run, not trusted from the prior claim: 327 passed, exit 0, 694.94s). The three follow-up bugfix commits (SECCION_DE_ADJUNTOS correction, broken multi-line Django comments, missing defer) are all confirmed fixed in the current tree, and a repo-wide sweep found no recurrence of either bug pattern elsewhere. All 16 spec scenarios (12 + 4) map to real behavioral evidence; 15/16 are fully compliant, and the 1 remaining scenario (genuine HEIC device-conversion) is honestly documented as partially verified rather than silently claimed complete. This is the same pattern the project's own convention treats as WARNING, not CRITICAL, when the gap is explicit, isolated, and the adjacent fallback path is fully proven -- unlike the CRITICAL precedent in the sincronizacion-numero-registro verify report, where the primary happy-path scenario had zero evidence of any kind.

Recommendation: archive is reasonable as-is, given the explicit, non-hidden nature of the one open gap and its narrow blast radius (client-only, iPhone-HEIC-specific, server-side re-validation is unaffected). If a real HEIC device sample becomes available before archive, running task 6.1 fully would make this a clean PASS with no caveats.
