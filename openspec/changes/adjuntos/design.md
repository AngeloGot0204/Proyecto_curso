# Design: Adjuntos (croquis/evidencia, backlog #11)

## Technical Approach

Four additive, independently rollback-able pieces: (1) a standalone `reportes/models.py::Adjunto` row per uploaded file, storing on the already-wired `STORAGES["default"]` (`config.storage.VercelBlobStorage`) exactly as `TipoDeReporte.logo`/`plantilla` do; (2) a dedicated upload endpoint plus a list view, so one attachment's rejection can never touch the step's `ValorDeReporte` writes; (3) a new `reportes/static/reportes/adjuntos.js` client module (HEIC→JPEG→compress→upload, best-effort, CDN-optional) queuing through the single shared Dexie owner bumped to `version(3)`; (4) a new `generador.py::_incrustar_adjuntos` primitive embedding up to 4 images into YAML-declared anchor cells. `paso`'s GET/POST behaviour, `_escribir_valores`, and `_intercambiar_logo` are all untouched.

## Architecture Decisions

### D1 — `Adjunto` is a `FileField`, not an `ImageField`

**Choice**: `archivo = models.FileField(upload_to="reportes/adjuntos/", max_length=500)` — no explicit `storage=`, inheriting `STORAGES["default"]` like every existing file field; `max_length=500` for the same reason documented on `TipoDeReporte.plantilla` (a full Vercel Blob public URL is stored as the name, and Django's 100-char default truncates it).

**Alternative rejected**: `ImageField` (the `logo` precedent). `ImageField.to_python` runs `PIL.Image.open` on every upload; Pillow cannot decode HEIC without `pillow-heif`, so the spec-mandated HEIC/HEIF allowlist entry would be rejected by Django before our own validator ever ran. Format enforcement therefore lives in `reportes/adjuntos.py`, not in the field class.

Field set (spec "Standalone Adjunto Model"): `reporte` FK (`CASCADE`, `related_name="adjuntos"`), `seccion_id` (`CharField(max_length=200)`, same width as `ValorDeReporte.identificador_de_campo`), `categoria` (`CategoriaDeAdjunto` TextChoices: `croquis`/`evidencia`), `archivo`, `nombre_original` (`CharField(max_length=255)`), `formato_original` (`CharField(max_length=100)` — the content-type **as received**, so a HEIC that reached us unconverted is auditable), `tamano_bytes` (`PositiveIntegerField`, server-measured), `autor` FK (`PROTECT`, mirroring `ValorDeReporte.autor`), `fecha_subida` (`DateTimeField(auto_now_add=True)`). Ordering is `("fecha_subida", "id")` — deterministic, and it is what fixes which attachments win the 4 Excel slots. No `unique` constraint: the spec forbids a count cap and the same photo may legitimately be attached twice.

### D2 — Separate endpoint, not the step's FormData POST

**Choice**: `POST /reportes/<id>/adjuntos/subir/`, one request per attachment, issued by `adjuntos.js` — **not** appended to the `<form>` the step submits.

**Alternative rejected**: one bundled multipart POST to `form.action`. `paso`'s POST is a Post/Redirect/Get that answers `302` and has no per-field error channel (`form.is_valid()` is called for effect only, every field is `required=False`, "never blocks"). A rejected file inside that body would have to either abort the redirect — losing the step's field values, exactly what "Per-Attachment Failure Isolation" forbids — or be silently swallowed. A separate endpoint gives each attachment its own status code and error id, keeps `paso-offline.js`'s `fetch(form.action, {body: new FormData(form)})` contract (change #10, D4) byte-for-byte unchanged, and makes offline retry per-attachment instead of per-step.

**Spec reconciliation**: the `adjuntos-reporte` scenario "Attachment queued via existing FormData submit path" names the mechanism (`FormData` over `fetch`, `credentials:"same-origin"`, one shared Dexie database), which this design preserves exactly; only the target URL differs. See Open Questions.

### D3 — Client pipeline in its own file, both CDN libraries optional

**Choice**: new `reportes/static/reportes/adjuntos.js`, bound to `input[type="file"][data-adjunto]` and no-op when absent (the `nuevo-reporte.js` D7 pattern). Rollback is "delete the file" (the `paso-offline.js`-not-`paso.js` precedent).

```
elegir archivo
  ├─ allowlist (content-type OR extensión)  ──falla──▶ error SOLO de este adjunto
  ├─ HEIC/HEIF y window.heic2any            ──▶ heic2any({toType:"image/jpeg"})
  ├─ window.imageCompression                ──▶ maxSizeMB:2, maxWidthOrHeight:2000
  ├─ lib ausente | throw | timeout           ──▶ seguir con el ORIGINAL
  └─ size > 8 MiB (8*1024*1024)              ──▶ error SOLO de este adjunto
```

Both `window.heic2any` and `window.imageCompression` are read defensively (`typeof … === "function"`), never awaited as a hard dependency — identical to the `typeof Dexie === "undefined"` guard both existing modules open with.

**Explicit deviation, flagged (rules.design)**: `capa-offline`'s design rejected the Workbox CDN precisely because it pulls a third-party origin *into the offline critical path*, and ADR-0001 mandates vanilla JS with no build. This change adds **two** CDN libraries to that same path, compounding the deviation the proposal already declared. It is accepted only because neither library is load-bearing: capture degrades to "upload the original under the ceiling", and the server re-validates regardless. Partial mitigation already exists — `sw.js`'s `esEstatico` branch (`url.origin !== self.location.origin`) caches cross-origin scripts cache-first, so both libraries survive offline after one successful online load, exactly as the Dexie CDN does today. Revisit if a bundler ever lands.

### D4 — `offline-db.js` `version(3)`, new `adjuntos_pendientes` store

**Choice**: in the single `.version()` owner, keep the existing `version(2)` block verbatim and append

```js
db.version(3).stores({ adjuntos_pendientes: "++id, reporteId, [reporteId+seccionId], estado" });
```

Dexie inherits unlisted stores from the previous version, so `borradores`/`nuevos` keep their shapes and the upgrade is a pure "add one object store" with no data migration. Row: `{ id, reporteId, seccionId, categoria, blob, nombreOriginal, formatoOriginal, tamanoBytes, estado: "pendiente"|"enviando"|"fallo", intentos, ultimoError, creadoEn }` — `Blob` values are stored natively by IndexedDB's structured clone, which is the ADR-0004 reason IndexedDB was chosen over `localStorage` in the first place.

**Alternatives rejected**: `[reporteId+seccionId]` as primary key (collides — no cap on attachment count per section); a second `Dexie(...)` instance (explicitly forbidden by the spec and by `offline-db.js`'s own header).

### D5 — `_incrustar_adjuntos`: coordinate-string anchors, injected files

**Choice**: `estructura` gains a top-level `adjuntos:` list of at most 4 slot dicts (`celda`, optional `ancho_px`/`alto_px`, defaults 320×240), mirroring the scalar `celda` declaration. Embedding uses openpyxl's **string** anchor form:

```python
def _incrustar_adjuntos(hoja, estructura, adjuntos):
    for slot, archivo in zip(estructura.get("adjuntos") or [], adjuntos):
        try:
            imagen = ImagenOpenpyxl(BytesIO(archivo.read()))
        except Exception:            # Pillow cannot decode it (e.g. an
            continue                 # unconverted HEIC) — skip, never fail
        imagen.width, imagen.height = _encajar(imagen, slot)
        hoja.add_image(imagen, slot["celda"])
```

**Why not reuse `_intercambiar_logo`'s mechanism**: that function must copy the loaded `anchor` *object* because a pre-existing drawing box already defines position **and** extent, and openpyxl then ignores `Image.width/height`. Attachments have no pre-existing drawing, so passing a coordinate string makes openpyxl build a `OneCellAnchor` whose `ext` is derived *from* `Image.width/height` — the inverse mechanism, which is why this is a generalization rather than a reuse. `zip` truncation is what enforces the 4-slot cap: extra attachments are simply never reached, staying stored and listable (spec scenario 2); no declared slots ⇒ empty list ⇒ zero iterations (scenario 4); no attachments ⇒ zero iterations (scenario 3).

**Injection, not query**: `generar_reporte(definicion, valores, adjuntos=())` gains one optional keyword; `reportes/views.py::generar` passes `[a.archivo for a in reporte.adjuntos.all()]`. `tipos_reporte` must not import `reportes` (dependency direction), and the default keeps every existing `generar_reporte(definicion, valores)` call — including the spec's own scenario wording — valid.

**Decode failures are skipped, never raised**: a stored HEIC (client conversion failed, server accepted it per the allowlist) makes `PIL.Image.open` raise. Turning that into `ProblemaDeGeneracion` would let one attachment block the whole document — the same failure mode the isolation requirement forbids one layer down. Skipped images are logged via `logger.exception`, matching `views.generar`'s existing convention.

### D6 — Anchor slots get notation validation, not merged-anchor validation

**Choice**: `validacion.py` gains R7, reusing the existing `_es_celda_valida` over `estructura["adjuntos"][*]["celda"]` and rejecting more than 4 slots, accumulated like every other rule (`regla="ancla-de-adjunto-mal-formada"` / `"anclas-de-adjunto-excedidas"`).

**Not applied**: R6's "must be the anchor of its merged range" and `_validar_colisiones_de_celda`. A floating image is anchored to a cell corner, not written into it, so a merged non-anchor cell is a legitimate target and overlapping a data cell is a template-layout choice, not a data collision. Without R7 an invalid coordinate would surface only at generation time as an openpyxl crash inside a user-facing action.

### D7 — Server validation is a pure module, shared by view and tests

**Choice**: new `reportes/adjuntos.py` holding `FORMATOS_PERMITIDOS`, `TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024`, `SECCION_DE_ADJUNTOS`, and `validar_adjunto(archivo) -> str | None` returning a stable error id (`formato-no-permitido`, `tamano-excedido`) or `None` — the same "stable `regla` id, free-form message" convention `ProblemaDeDefinicion`/`ProblemaDeGeneracion` already use. Pure over an `UploadedFile`, so it is unit-testable with no DB, mirroring `validacion.py`'s R1–R4 posture. The view calls it *before* any `Adjunto.objects.create`, so a rejected upload creates no row and writes no blob.

## Data Flow

```
[paso.html · S-08]                    [adjuntos.js]                 [servidor]
  input[type=file]
  data-adjunto  ──change──▶ allowlist ─▶ heic2any? ─▶ compress? ─▶ ≤8MiB?
                                │ (cualquier fallo ⇒ original)      │
                                │                                   ├─ok──▶ FormData
                                │                                   │      POST /reportes/<id>/adjuntos/subir/
                                └─error──▶ chip "solo este adjunto" │        │
                                                                    │        ├ 201 → chip OK (el paso NO se toca)
   offline / fetch rechaza ──▶ adjuntos_pendientes{estado:"pendiente"}       ├ 400 {"error": "<id>"} → chip error
                                    │                                        ├ 302 /login/ → estado:"fallo" (fila intacta)
                                    └─[Reintentar]──▶ reenvía el blob ──────▶└ 404 → sin acceso

   POST del paso  ──── fetch(form.action, FormData) ────▶ paso(): ValorDeReporte  (ruta intacta, #10 D4)

   generar ──▶ generar_reporte(definicion, valores, adjuntos=[a.archivo …])
                    ├ _intercambiar_logo(hoja, tipo.logo)          (sin cambios)
                    ├ _escribir_valores(...)                        (sin cambios)
                    └ _incrustar_adjuntos(hoja, estructura, adjuntos)  zip ⇒ máx 4
```

Attachment state machine (`adjuntos_pendientes`), deliberately narrower than `borradores`': there is no `borrador` state — a row exists only once an upload has been attempted and has not yet succeeded; success **deletes** the row (#9's clear-on-success contract) and `reconciliar()` on load re-renders the per-attachment retry chip without ever retrying automatically (ADR-0004 / S-15).

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reportes/models.py` | Modify | `CategoriaDeAdjunto`, `Adjunto` (D1) |
| `reportes/migrations/0006_adjunto.py` | Create | Single additive `CreateModel` |
| `reportes/adjuntos.py` | Create | Allowlist, ceiling, section constant, `validar_adjunto` (D7) |
| `reportes/views.py` | Modify | `subir_adjunto` (POST, JSON), `adjuntos_de_reporte` (GET list); `generar` passes `adjuntos=` |
| `reportes/urls.py` | Modify | `adjuntos/` + `adjuntos/subir/` routes |
| `reportes/static/reportes/adjuntos.js` | Create | Pipeline, queue, per-attachment chips/retry (D3) |
| `reportes/static/reportes/offline-db.js` | Modify | `version(3)` + `adjuntos_pendientes` (D4) |
| `reportes/templates/reportes/paso.html` | Modify | Two CDN `<script>`s, `adjuntos.js`, file input + `data-adjuntos-url` when `permite_adjuntos` |
| `reportes/templates/reportes/adjuntos.html` | Create | List + download links |
| `tipos_reporte/generador.py` | Modify | `_incrustar_adjuntos`, `generar_reporte(..., adjuntos=())` (D5) |
| `tipos_reporte/validacion.py` | Modify | R7 anchor-slot rules (D6) |
| `reportes/tests/test_adjuntos.py` | Create | Model, validator, endpoint, isolation, listing |
| `tipos_reporte/tests/test_generador.py` | Modify | Four embedding scenarios |
| `tipos_reporte/tests/test_validacion_plantilla.py` | Modify | R7 scenarios |

## Interfaces / Contracts

```python
# reportes/adjuntos.py
FORMATOS_PERMITIDOS = {
    "image/jpeg": (".jpg", ".jpeg"), "image/png": (".png"),
    "image/webp": (".webp"), "image/heic": (".heic"), "image/heif": (".heif"),
}                                    # client mirror lives in adjuntos.js
TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024
```

| Route | Method | Body / Response |
|---|---|---|
| `reportes_adjuntos_subir` `/reportes/<id>/adjuntos/subir/` | POST | `FormData{csrfmiddlewaretoken, seccion_id, categoria, archivo}` → `201 {"id","nombre","url","tamano_bytes"}` · `400 {"error":"formato-no-permitido"\|"tamano-excedido"\|"archivo-ausente"\|"seccion-no-admite-adjuntos"}` · `404` (absent **or** no access, `_reporte_accesible`) |
| `reportes_adjuntos` `/reportes/<id>/adjuntos/` | GET | HTML list: `nombre_original`, `categoria`, `fecha_subida`, `autor`, `tamano_bytes`, `<a href="{{ adjunto.archivo.url }}">` |

`JsonResponse` is new to this codebase (existing views use `messages` + redirect). It is required here: a redirect carries no per-attachment outcome, which is the whole point of D2.

Access uses the existing `_reporte_accesible` shim (creator or invited participant) for both routes — same 404-for-everything, no existence leak.

## Testing Strategy

| Layer | What to test | Approach |
|-------|--------------|----------|
| Unit (pytest, RED first) | `validar_adjunto`: each allowed type, disallowed type, 8 MiB boundary (`==` accepted, `+1` rejected) | `SimpleUploadedFile`, no DB |
| Unit | `_incrustar_adjuntos`: 3-of-4 embedded, 6→4 embedded, 0 attachments, no declared slots, undecodable file skipped | Real workbook via `plantilla_xlsx`, assert `len(hoja._images)` and each `anchor._from` |
| Unit | R7: malformed anchor, >4 slots | Plain dict, `validar_estructura` |
| Integration | Upload happy path creates one `Adjunto` (not a `ValorDeReporte`); oversized/disallowed → 400 + `Adjunto.objects.count() == 0`; N attachments accepted (no cap); non-participant → 404; list view renders metadata + link | Django test client, `sesion_de_creador` fixture |
| Integration | **Isolation**: POST the step with valid values, then POST an oversized attachment → values persisted **and** step 302 unchanged | Two requests, asserting the step outcome is independent |
| Client JS | none automated | No JS runner exists (spec Out of Scope) — manual DevTools script, `tasks.md` Phase 4, same pattern as #9/#10 |

Manual DevTools verification is mandatory for: HEIC conversion against a **real iPhone-captured** file; both-CDN-blocked fallback (DevTools ▸ Network ▸ block request URL) still uploading the original; `adjuntos_pendientes` rows appearing/clearing under Offline→Online; and the v2→v3 IndexedDB upgrade preserving existing `borradores` rows. The script itself belongs to `tasks.md`, not here.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Untrusted file parsing | **Applicable** — attacker-controlled bytes reach Pillow/openpyxl at generation time | Allowlist + ceiling before persistence (D7); every decode wrapped in `try/except … continue` inside `_incrustar_adjuntos` (D5), never an uncaught exception or a blocked document | undecodable-file-skipped generator test |
| Executable-file classification | **Applicable** — a stored file is later served for download | Allowlist is raster-image-only (no SVG, no HTML); `Content-Disposition` comes from storage/Blob, filename never echoed into a header from user input | disallowed-content-type 400 test |
| Routing | **Applicable** — two new authenticated routes | Both use `_reporte_accesible`; POST is `@login_required @require_POST`; `seccion_id` is checked against `SECCION_DE_ADJUNTOS`, never trusted from the client | no-access → 404; wrong section → 400 |
| Shell / subprocess | N/A — none introduced | | |
| VCS/PR automation | N/A — none introduced | | |
| Process integration | N/A — none introduced | | |

Known, accepted limitation (unchanged from `plantilla`/`logo` today): `VercelBlobStorage` returns a **public** blob URL, so the download link is unauthenticated-but-unguessable. The *list* is access-scoped; the blob itself is not. Proxying downloads through Django is out of scope here.

## Migration / Rollout

One forward migration (`0006_adjunto`, `CreateModel` only — no existing table is altered). Rollback: `migrate reportes 0005`, delete `adjuntos.py`/`adjuntos.js`/`adjuntos.html`, revert the two routes, the `paso.html` tags, `offline-db.js` back to `version(2)`, and remove `_incrustar_adjuntos` plus the `adjuntos=` keyword (logo and value writing are separate functions and stay green). Two client-side rollback notes: an already-installed browser keeps IndexedDB at v3 — harmless, since v2 code never names the extra store; and `sw.js` has cached the two CDN scripts under `reportes-offline-v1`, so a rollback should bump `CACHE` to evict them.

`VercelBlobStorage.exists()` always returns `False`, so no cleanup runs on delete/replace — orphan blobs accumulate. Documented in the proposal, out of scope.

## Open Questions

- [ ] The `adjuntos-reporte` scenario "Attachment queued via existing FormData submit path" reads literally as *sync through `fetch(form.action, …)`*; D2 keeps that mechanism but targets the attachment endpoint, since bundling would violate the same spec's isolation requirement. Confirm the reading, or amend that one scenario line before `sdd-verify`.
- [ ] `SECCION_DE_ADJUNTOS` needs the real S-08 `seccion.id` from the production definition YAML — the sample definitions in `media/` are empty (`secciones: []`). Confirm before apply.
- [ ] Anchor-slot box defaults (320×240 px, aspect-preserving fit) are an assumption; confirm against the real `.xlsx` layout once the template declares its four slots.
- [ ] Pinned CDN versions/SRI for `heic2any` and `browser-image-compression` — the existing Dexie tag uses `crossorigin="anonymous"` with no `integrity`. Match that precedent, or tighten both at once?
