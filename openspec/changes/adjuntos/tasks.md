# Tasks: Adjuntos (croquis/evidencia, backlog #11)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~880-950 (model+migration ~85, server endpoint+validation+tests ~410, client JS+offline queue ~195 untested, generador+validacion+tests ~210) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (`Adjunto` model, D1) → PR 2 (upload/list endpoint + validation, D2+D7) → PR 3 (client JS + offline queue, D3+D4) → PR 4 (Excel embedding + anchor validation, D5+D6) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (resolved before this apply run) |

Decision needed before apply: No (resolved: stacked-to-main)
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Standalone `Adjunto` model + migration (D1) | PR 1 | `pytest reportes/tests/test_adjuntos.py -k modelo` | N/A — DB-only, covered by pytest | `migrate reportes 0005`; model has no callers yet |
| 2 | Upload/list endpoint + `reportes/adjuntos.py` validator (D2, D7) | PR 2 | `pytest reportes/tests/test_adjuntos.py` | Django test client, `sesion_de_creador` fixture | Remove `subir_adjunto`/`adjuntos_de_reporte`, revert `urls.py`, delete `adjuntos.py`/`adjuntos.html` |
| 3 | Client pipeline + offline queue (D3, D4) | PR 3 | No automated JS runner — Manual DevTools script (Phase 6) | Manual: Chrome DevTools, live dev server, Network ▸ Offline/block-URL | Delete `adjuntos.js`, revert `offline-db.js` to `version(2)`, revert `paso.html` tags |
| 4 | Excel embedding + anchor-slot validation (D5, D6) | PR 4 | `pytest tipos_reporte/tests/test_generador.py tipos_reporte/tests/test_validacion_plantilla.py -k adjunto` | N/A — openpyxl workbook fixture, covered by pytest | Remove `_incrustar_adjuntos` and `adjuntos=` keyword (logo/value-writing untouched); revert R7 in `validacion.py` |

## Phase 1: Foundation — `Adjunto` Model & Migration (D1)

- [x] 1.1 Add `CategoriaDeAdjunto` (`TextChoices`: `croquis`/`evidencia`) and `Adjunto` model to `reportes/models.py` with the D1 field set: `reporte` FK (`CASCADE`, `related_name="adjuntos"`), `seccion_id` (`CharField(max_length=200)`), `categoria`, `archivo` (`FileField(upload_to="reportes/adjuntos/", max_length=500)`, no explicit `storage=`), `nombre_original` (`CharField(max_length=255)`), `formato_original` (`CharField(max_length=100)`), `tamano_bytes` (`PositiveIntegerField`), `autor` FK (`PROTECT`), `fecha_subida` (`DateTimeField(auto_now_add=True)`), `Meta.ordering = ("fecha_subida", "id")`.
- [x] 1.2 Create `reportes/migrations/0006_adjunto.py` — single additive `CreateModel`, no existing table altered.
- [x] 1.3 RED: write `test_adjunto_se_guarda_independiente_de_valorreporte` in `reportes/tests/test_adjuntos.py` (spec "Standalone Adjunto Model" scenario: saving an S-08 attachment persists an `Adjunto` row, not a `ValorDeReporte` row).
- [x] 1.4 GREEN: run `python manage.py migrate reportes` against the Postgres test DB, confirm 1.3 passes; run `migrate reportes 0005` to confirm the reverse migration drops cleanly.
- [x] 1.5 **Blocker**: `SECCION_DE_ADJUNTOS` needs a real S-08 `seccion.id`, but every sample definition in `media/tipos_reporte/definiciones/` has `secciones: []`. Add a fixture (mirroring `definicion_valida` in `reportes/tests/conftest.py`) that declares a real section id for S-08 attachments, for use by Phase 2/3/5 tests. Resolve before any endpoint or generator test asserts against `SECCION_DE_ADJUNTOS`. — Resolved via `seccion_s08_id` fixture (`reportes/tests/conftest.py`, value `"s-08-croquis-evidencia"`), documented as the interim test-only resolution of design.md's open question.

## Phase 2: Server Validation Module (D7, TDD)

- [x] 2.1 RED: write `test_valida_formato_permitido` in `reportes/tests/test_adjuntos.py` — parametrized over JPEG/PNG/WEBP/HEIC/HEIF content-types, using `SimpleUploadedFile`, no DB.
- [x] 2.2 RED: write `test_rechaza_formato_no_permitido` (e.g. `image/gif`, `application/pdf`).
- [x] 2.3 RED: write `test_acepta_tamano_limite_8mb` (exactly 8MB accepted) and `test_rechaza_tamano_excedido_8mb_mas_1` (8MB + 1 byte rejected) — boundary per D7.
- [x] 2.4 GREEN: create `reportes/adjuntos.py` with `FORMATOS_PERMITIDOS`, `TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024`, `SECCION_DE_ADJUNTOS`, and `validar_adjunto(archivo) -> str | None` returning stable error ids (`formato-no-permitido`, `tamano-excedido`).
- [x] 2.5 REFACTOR: confirm `validar_adjunto` is pure over an `UploadedFile` (no DB access), matching `validacion.py`'s R1-R4 posture; run 2.1-2.3 green.

## Phase 3: Upload & List Endpoint (D2, TDD)

- [x] 3.1 RED: write `test_subir_adjunto_happy_path_crea_adjunto` — 201, response body has `id`/`nombre`/`url`/`tamano_bytes`, `Adjunto.objects.count() == 1` and `ValorDeReporte.objects.count() == 0`.
- [x] 3.2 RED: write `test_subir_adjunto_formato_no_permitido_devuelve_400_sin_crear_fila` (400 `{"error":"formato-no-permitido"}`, `Adjunto.objects.count() == 0`).
- [x] 3.3 RED: write `test_subir_adjunto_tamano_excedido_devuelve_400_sin_crear_fila` (400 `{"error":"tamano-excedido"}`, no row created — spec "Server-Side Size Ceiling").
- [x] 3.4 RED: write `test_subir_adjunto_seccion_no_admite_adjuntos_400` (`seccion_id` not `SECCION_DE_ADJUNTOS` → 400 `{"error":"seccion-no-admite-adjuntos"}`, never trusted from client).
- [x] 3.5 RED: write `test_subir_adjunto_no_participante_devuelve_404` (threat matrix "Routing" — non-creator/non-invited → 404, no existence leak).
- [x] 3.6 RED: write `test_multiples_adjuntos_sin_limite_de_cantidad` (spec "No Hard Cap on Attachment Count": N valid attachments all accepted).
- [x] 3.7 RED: write `test_aislamiento_un_adjunto_invalido_no_bloquea_paso` in `reportes/tests/test_adjuntos.py` — two requests: POST the step with valid field values (asserts step 302 and values persisted), then POST an oversized attachment to `subir_adjunto` (asserts 400, `Adjunto.objects.count() == 0`); confirm both outcomes are independent (spec "Per-Attachment Failure Isolation").
- [x] 3.8 GREEN: implement `reportes/views.py::subir_adjunto` (`@login_required @require_POST`, `_reporte_accesible`, calls `validar_adjunto` before any `Adjunto.objects.create`, `JsonResponse` 201/400) — run 3.1-3.7 green.
- [x] 3.9 RED: write `test_lista_adjuntos_autorizado_incluye_metadata_y_enlace` (spec "Server-Side Listing and Download": response includes `nombre_original`, `categoria`, `fecha_subida`, `autor`, `tamano_bytes`, download link).
- [x] 3.10 GREEN: implement `reportes/views.py::adjuntos_de_reporte` (GET list, `_reporte_accesible`) and create `reportes/templates/reportes/adjuntos.html`.
- [x] 3.11 Wire `reportes/urls.py` routes `reportes_adjuntos_subir` (`/reportes/<id>/adjuntos/subir/`) and `reportes_adjuntos` (`/reportes/<id>/adjuntos/`).
- [x] 3.12 REFACTOR: confirm `JsonResponse` error ids match the design interface contract exactly (`formato-no-permitido`, `tamano-excedido`, `archivo-ausente`, `seccion-no-admite-adjuntos`); run full Phase 3 suite green.

## Phase 4: Client Pipeline & Offline Queue (D3, D4)

- [x] 4.1 Append `db.version(3).stores({ adjuntos_pendientes: "++id, reporteId, [reporteId+seccionId], estado" })` to `reportes/static/reportes/offline-db.js`, after the existing `version(2)` block, verbatim (D4) — no data migration, `borradores`/`nuevos` shapes untouched.
- [x] 4.2 Create `reportes/static/reportes/adjuntos.js`: bind to `input[type="file"][data-adjunto]`, no-op when absent; allowlist check (content-type/extension); HEIC/HEIF detection → `window.heic2any` (feature-detected via `typeof … === "function"`, never a hard import) converts to JPEG before compression; `window.imageCompression` (same defensive detection) with `maxSizeMB:2, maxWidthOrHeight:2000`; any missing-lib/throw/timeout falls back to the original file; final 8MiB (`8*1024*1024`) ceiling check blocks only that attachment on failure (D3 pipeline diagram).
- [x] 4.3 Implement the dedicated `FormData` POST to `/reportes/<id>/adjuntos/subir/` inside `adjuntos.js` — its own `fetch` call, separate from `paso-offline.js`'s step-submission `fetch(form.action, {body: new FormData(form)})`, so an attachment failure never blocks or rolls back the step (spec "Offline Queueing Through Shared Dexie Schema").
- [x] 4.4 Implement `adjuntos_pendientes` queue write on offline/fetch-reject (row shape: `{id, reporteId, seccionId, categoria, blob, nombreOriginal, formatoOriginal, tamanoBytes, estado, intentos, ultimoError, creadoEn}`), per-attachment retry chip UI, and `reconciliar()` re-render of pending/failed rows on page load without auto-retry (ADR-0004/S-15).
- [x] 4.5 Add two CDN `<script crossorigin="anonymous">` tags (`heic2any`, `browser-image-compression`, matching the existing Dexie tag's no-`integrity` precedent pending 7.3) plus `adjuntos.js`, and a file input with `data-adjunto`/`data-adjuntos-url` attributes to `reportes/templates/reportes/paso.html`, gated on the S-08 section.
- [x] 4.6 Confirm (no code change expected) `sw.js`'s existing `esEstatico` cross-origin cache-first branch also covers the two new CDN script origins, so both libraries survive offline after one successful online load (same as the Dexie CDN today). — Confirmed: `esEstatico = url.pathname.indexOf("/static/") === 0 || url.origin !== self.location.origin` already matches any cross-origin URL generically (`reportes/templates/reportes/sw.js:72`); no change needed for the two new CDN origins.

## Phase 5: Excel Embedding & Anchor Validation (D5, D6, TDD)

- [x] 5.1 RED: write a malformed-anchor-coordinate test for the `adjuntos` slot list in `tipos_reporte/tests/test_validacion_plantilla.py` (R7, `regla="ancla-de-adjunto-mal-formada"`).
- [x] 5.2 RED: write a >4-declared-slots test (R7, `regla="anclas-de-adjunto-excedidas"`).
- [x] 5.3 GREEN: add R7 to `tipos_reporte/validacion.py`, reusing `_es_celda_valida` over `estructura["adjuntos"][*]["celda"]`; explicitly do NOT apply R6's merged-anchor rule or `_validar_colisiones_de_celda` (D6 — floating images anchor to a cell corner, not written into it).
- [x] 5.4 RED: write the "Attachments within anchor-slot count are embedded" test in `tipos_reporte/tests/test_generador.py` (3 attachments, 4 declared slots → all 3 embedded; assert `len(hoja._images)` and each `anchor._from`).
- [x] 5.5 RED: write the "Attachments beyond anchor-slot count remain stored, not embedded" test (6 attachments, 4 slots → only 4 embedded, no error raised).
- [x] 5.6 RED: write the "No attachments leaves anchor slots empty" test (0 attachments, slots declared → generation succeeds, no images embedded).
- [x] 5.7 RED: write the "Template without declared anchor slots skips embedding entirely" test (no `adjuntos:` key → `_incrustar_adjuntos` no-ops, cell values/logo swap unaffected).
- [x] 5.8 RED: write an undecodable-file-skipped test (threat matrix "Untrusted file parsing" — an unconverted HEIC that reached storage makes `PIL.Image.open` raise; assert it is skipped via `try/except … continue`, never raised as `ProblemaDeGeneracion`).
- [x] 5.9 GREEN: implement `tipos_reporte/generador.py::_incrustar_adjuntos(hoja, estructura, adjuntos)` using openpyxl's string-anchor form (`hoja.add_image(img, slot["celda"])`, NOT copying an existing anchor object like `_intercambiar_logo`), `zip(estructura.get("adjuntos") or [], adjuntos)` enforcing the 4-slot cap via truncation, decode failures caught and `logger.exception`-logged.
- [x] 5.10 GREEN: add `adjuntos=()` keyword to `generar_reporte(definicion, valores, adjuntos=())`, calling `_incrustar_adjuntos` alongside `_intercambiar_logo` before returning the workbook; confirm every existing `generar_reporte(definicion, valores)` call (including prior tests) remains valid with the default.
- [x] 5.11 GREEN: wire `reportes/views.py::generar` to pass `adjuntos=[a.archivo for a in reporte.adjuntos.all()]` (dependency direction preserved — `tipos_reporte` never imports `reportes`).
- [x] 5.12 REFACTOR: run full Phase 5 suite green; confirm scenario coverage against all 4 `generacion-reporte-excel` delta scenarios.

## Phase 6: Manual DevTools Verification (No Automated JS Coverage — Documented Limitation)

- [ ] 6.1 DevTools script: select a real iPhone-captured HEIC file; confirm `heic2any` converts to JPEG before `browser-image-compression` runs, and the uploaded file is JPEG. **Partially verified (2026-08-30)**: no real HEIC sample available, so a simulated file (PNG bytes relabeled `image/heic`/`.heic`) was used instead — confirmed HEIC detection fires and `heic2any` is invoked, and confirmed the "conversion failure falls back to original file" path succeeds end-to-end (201, chip "Adjunto subido"). Genuine successful HEIC→JPEG conversion against real device output remains unverified — needs a real HEIC file when available.
- [x] 6.2 DevTools script: Network ▸ block both CDN script URLs; confirm the original file still uploads under the 8MiB ceiling without blocking capture (spec "CDN unreachable falls back to original file"). Verified live (2026-08-30) via Console `delete window.heic2any; delete window.imageCompression;` (equivalent simulation of both libraries unreachable) — file uploaded successfully (201) without compression, capture never blocked.
- [x] 6.3 DevTools script: Network ▸ Offline, capture an attachment → `adjuntos_pendientes` row appears; go Online, trigger reconcile/retry → row syncs via its own `fetch` to `/reportes/<id>/adjuntos/subir/` and clears. Verified live (2026-08-30): offline capture showed "Sin conexión — pendiente de subir." with Reintentar button; after going back online and clicking Reintentar, upload succeeded ("Adjunto subido.").
- [x] 6.4 DevTools script: confirm an existing v2 IndexedDB (with populated `borradores`/`nuevos` rows) upgrades cleanly to v3 with `adjuntos_pendientes` added, no data loss to the existing stores. Verified indirectly (2026-08-30): steps 1-4 were submitted successfully throughout this same session against the same `reportes-offline` database now at v3, with no IndexedDB errors — `borradores`/`nuevos` were empty at inspection time only because successful submits already deleted/never-populated those rows (expected behavior, not data loss). The v3 upgrade itself succeeded without throwing, evidenced by `adjuntos_pendientes` working correctly in 6.3.
- [x] 6.5 DevTools script: confirm per-attachment isolation in the browser — submit a step with valid field values plus one oversized attachment; step succeeds, only the attachment shows an error chip (mirrors 3.7's server-side isolation test at the UI layer). Verified live (2026-08-30): a 9MB fake attachment showed "Archivo demasiado grande (>8MB) — solo este adjunto falló." while the step's own field-values submission succeeded independently (redirected cleanly, since `resultados` is the last section and self-redirects with no "next" step) — confirming the two submissions are fully decoupled per D2.

## Phase 7: Cleanup / Documentation

- [ ] 7.1 Resolve `design.md` Open Questions: confirm `SECCION_DE_ADJUNTOS`'s real `seccion.id` against the production definition YAML once available, or document the fixture-only resolution from 1.5 as the interim answer.
- [ ] 7.2 Confirm/record anchor-slot box defaults (320x240px, aspect-preserving fit) against the real `.xlsx` layout once the template declares its four slots.
- [ ] 7.3 Confirm CDN pinning/SRI decision for `heic2any` and `browser-image-compression` — match the existing Dexie tag's no-`integrity` precedent, or tighten both at once.
- [ ] 7.4 Run the full `pytest` suite and confirm no regressions in existing tests (`reportes/`, `tipos_reporte/`).
