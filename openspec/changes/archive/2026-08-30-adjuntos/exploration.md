# Exploration: Adjuntos (croquis/evidencia, backlog #11)

## Current State

- **Data model**: `tipos_reporte/models.py::TipoDeDato` is a CLOSED catalog (`texto, numero, fecha, hora, seleccion, booleano, rango-hora-inicio-fin`). No file/image type exists; `reportes/formularios.py::_campo_escalar` raises `ValueError` for anything else. Attachments are therefore NOT modeled today as a declarative-definition field/value like other captured data — matching PRD's own data dictionary, which describes `Adjunto` as a distinct entity, separate from `ValorDeReporte`.
- **Storage backend already exists**: `config/storage.py::VercelBlobStorage` (Django `Storage`), wired via `STORAGES["default"]` in `config/settings.py` (gated `not DEBUG`: prod → Vercel Blob, dev/test → `FileSystemStorage`/`MEDIA_ROOT`). Already used by `TipoDeReporte.logo` (`ImageField`) and `TipoDeReporte.plantilla`/`DefinicionDeTipo.archivo_yaml` (`FileField(max_length=500)`, extended because Blob URLs exceed Django's default 100-char limit). A new `Adjunto.archivo` field reuses this for free.
- **Offline/sync architecture (#9, #10, both archived)**: `reportes/static/reportes/offline-db.js` owns the single shared Dexie schema (`reportes-offline`, stores `borradores`+`nuevos`) — any new consumer must reuse `window.reportesOfflineDB`, never call `.version()` again. `paso-offline.js` already POSTs via `fetch(form.action, {body: new FormData(form), ...})` — `FormData` natively carries `File`/`Blob`, so the existing fetch pipeline is structurally attachment-capable with no rework. Actual sync granularity (confirmed in `reportes/views.py::paso`) is one fetch POST per wizard step, not per role-section as ADR-0004's prose literally states.
- **IndexedDB choice precedent**: ADR-0004 chose IndexedDB over `localStorage` specifically because `localStorage`'s ~5MB text-only cap could not hold the S-08 croquis/evidencia image — i.e. "store the image Blob locally, compress before upload" was already anticipated by the offline ADR.
- **Excel generation (`tipos_reporte/generador.py`)**: `_intercambiar_logo` is the ONLY image-embedding code — a single-image, fixed-anchor swap (reuses the template's pre-existing `openpyxl` anchor for the logo). `_escribir_valores` only ever writes cell VALUES for every other field. **Whether attachments must be embedded into the generated `.xlsx` at all is unsettled by PRD/TECH-DESIGN/DESIGN** — this is a real open decision; if yes, `generador.py` needs a new multi-image-anchor primitive that doesn't exist.
- **`Reporte` lifecycle**: `EstadoDeReporte` is `EN_PROGRESO`/`TERMINADO` only — no attachment state exists.
- **RESOLUCION-ADVERSARIAL.md decision #13** (cited by ADR-0004): automatic on-device compression, no explicit size limit (compression bounds it indirectly), Vercel Blob storage.
- **PRD "casos borde" + DESIGN error table**: an oversized/unsupported attachment must block only the attachment, never the rest of the report — this is the backlog item's "bloqueo solo del adjunto" requirement, independently corroborated in two artifacts.

## Affected Areas

- `reportes/models.py` — new `Adjunto` model (FK `Reporte`, file field on `VercelBlobStorage`, likely section binding, autor, fecha, format/status fields).
- `tipos_reporte/models.py` — only if `TipoDeDato` gains an image/file type (Approach 2 below); untouched under Approach 1.
- `reportes/formularios.py` — only affected under Approach 2.
- `reportes/views.py::paso` — needs an upload endpoint/handling path for `Adjunto`.
- `reportes/static/reportes/paso-offline.js`, `offline-db.js` — client-side compression, a new Dexie shape for pending attachment blobs (through the single shared schema owner), and "block only the attachment" retry/error UI.
- `tipos_reporte/generador.py` — only if the proposal decides attachments must render into the generated Excel.
- `config/storage.py`, `config/settings.py::STORAGES` — reusable as-is.
- `reportes/templates/reportes/paso.html` — new file input on S-08's section template, following the existing `data-*` attribute contract.

## Approaches

1. **Standalone `Adjunto` model, fully outside the declarative-definition system** — FK to `Reporte`, hardcoded to its capturing section, own upload view/JS module (mirroring `nuevo-reporte.js`'s no-op-if-absent form-hook pattern).
   - Pros: zero changes to `TipoDeDato`/`formularios.py`/`generador.py`'s value-writing path; smallest, most isolated slice; matches PRD's own framing; trivially satisfies "block only the attachment" since it never touches `ValorDeReporte` or the per-step POST success path.
   - Cons: not visible to the closed `TipoDeDato` catalog, so a future second attachment-bearing report type needs ad hoc handling, not configuration; if Excel embedding is required, `generador.py` still needs bespoke code regardless.
   - Effort: Medium.

2. **Extend `TipoDeDato` with an `IMAGEN`/`ARCHIVO` type, fully declarative** — flows through `_iterar_nodos`, `construir_formulario_seccion`, `ValorDeReporte` (Blob URL as `valor` text), and a generalized `generador.py` image-anchor writer.
   - Pros: consistent with ADR-0003's "new report type = configuration, not code" goal.
   - Cons: widest surface touched; stretches `ValorDeReporte`'s single-`TextField` contract (design D1 of backlog #5) to hold a Blob URL, not a clean fit; "block only the attachment" becomes harder once it shares the per-step validation/POST path with every other field.
   - Effort: High.

3. **Hybrid — standalone `Adjunto` model (as #1) + a lightweight `permite_adjunto: true` flag per section** in the definition YAML, without a new `TipoDeDato`.
   - Pros: keeps #1's isolation while giving future report types a configuration point instead of a hardcoded section.
   - Cons: adds a small validation-surface touch in `tipos_reporte/validacion.py`; most of #1's effort still applies.
   - Effort: Medium.

4. **Compression library choice (orthogonal axis)**: hand-rolled `<canvas>`-based JPEG re-encode vs. a CDN compression library.
   - Pros (hand-rolled): matches ADR-0001's vanilla-JS/no-build stance and the project's demonstrated pattern of rejecting third-party CDN dependencies in offline-critical paths (capa-offline's design explicitly rejected Workbox CDN for a similar reliability concern).
   - Cons (hand-rolled): reinvents EXIF-orientation and format-edge-case handling a maintained library already covers.
   - Effort: Low either way, independent of the model approach.

## Recommendation

Approach 1 for the model shape (smallest correct slice, matches PRD's data-dictionary framing, cleanly satisfies "bloqueo solo del adjunto"), with the compression sub-decision leaning hand-rolled `<canvas>` per the codebase's consistent no-third-party-CDN posture — genuinely open pending proposal-time input. Approach 2 is disproportionate to a single MVP attachment slot (S-08 only). Approach 3 is a reasonable future upgrade (e.g. when #13/admin CRUD or a second report type needs it) but premature now.

## Open Decisions (must be settled in proposal)

1. Does the generated Excel embed attachments, or do they stay server-side-only (linked/listed, never written into the `.xlsx`)?
2. Hand-rolled `<canvas>` compression vs. a CDN compression library?

## Risks

- Whether attachments must embed into the generated `.xlsx` is unsettled by any artifact — must be an explicit proposal decision; `generador.py` has no reusable multi-image primitive today.
- No format/size enforcement precedent exists anywhere (`logo`/`plantilla`/`archivo_yaml` have no validators) — both client- and server-side format/size blocking are new patterns for this project.
- Offline capture of a compressed image blob has no automated test path (same "no JS runner" constraint every prior offline change hit) — manual DevTools script only.
- `VercelBlobStorage.exists()` always returns `False`, content-addressed via `addRandomSuffix` — fine for create-once files; if attachments are ever replaced in place, orphaned blobs accumulate with no cleanup mechanism.
- Any new Dexie store/shape must go through the single shared `offline-db.js` `.version()` owner — a naive second `Dexie(...)` call would break the existing shared-schema contract.

## Key Learnings

1. `TipoDeDato`'s closed catalog has no file/image type — attachments are architecturally outside `ValorDeReporte` by current design, matching PRD's own data-dictionary framing.
2. `config/storage.py::VercelBlobStorage` already exists and is reused by `TipoDeReporte.logo`/`plantilla` — a new `Adjunto.archivo` field needs zero new infra work.
3. `generador.py::_intercambiar_logo` is single-image/fixed-anchor only — embedding N attachments into the generated Excel needs a new primitive, not a generalization.
4. `paso-offline.js`'s existing fetch-based submit already uses `FormData`, which natively supports `File`/`Blob`, so the fetch layer needs no rework for attachment upload.
5. Sync granularity is actually one fetch POST per wizard step (confirmed in `reportes/views.py::paso`), not per role-section as ADR-0004's prose literally states — worth double-checking against the real code again at design time.

**Next**: sdd-propose (pending the two open decisions above)
