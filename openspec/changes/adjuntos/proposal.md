# Proposal: Adjuntos (croquis/evidencia, backlog #11)

## Intent

Field auditors capturing S-08 ("croquis/evidencia") today have no way to
attach a photo or sketch to a `Reporte` — `TipoDeDato`'s closed catalog has
no file/image type, and PRD frames `Adjunto` as its own entity, distinct
from `ValorDeReporte`. This change adds attachment capture (upload, offline
queueing, client-side compression, server storage) and makes those
attachments appear both in the generated `.xlsx` and in the report's
server-side record, closing the last data-capture gap before #12/#13.

## Scope

### In Scope
- `reportes/models.py::Adjunto` — standalone model, FK to `Reporte`, file
  field on `VercelBlobStorage` (reused as-is), category (`croquis`/
  `evidencia`), autor, timestamps, original filename, size, content-type.
  Hardcoded to S-08; outside `TipoDeDato`/`ValorDeReporte`.
- Upload endpoint in `reportes/views.py::paso` path — one attachment
  succeeds/fails independently ("bloqueo solo del adjunto").
- Format allowlist: JPEG, PNG, WEBP, **and HEIC/HEIF** (client + server,
  identical list — HEIC is common on iPhone camera captures and must be
  accepted per user decision). Hard size ceiling: reject >8MB
  pre-compression/pre-conversion as a backstop (typical phone photos fit
  well under this; compression is the primary bound per
  RESOLUCION-ADVERSARIAL.md #13).
- Client-side HEIC→JPEG conversion via a second CDN-loaded library
  (`heic2any`) run BEFORE compression, since HEIC has no native decode path
  in Chrome/Firefox canvas (`browser-image-compression` itself has no HEIC
  support — it relies on `<canvas>`, which cannot draw an undecoded HEIC
  source in non-Safari browsers). Pipeline becomes: HEIC detected (by
  `content-type`/extension) → `heic2any` converts to JPEG → normal
  `browser-image-compression` pass. Non-HEIC formats skip straight to
  compression. This adds a second WASM-backed CDN dependency and a slower,
  more failure-prone conversion step — documented as an explicit added
  cost/risk below, not silently absorbed into the original single-library
  plan.
- Client-side compression via a CDN-loaded library (`browser-image-compression`
  — actively maintained, promise-based, `maxSizeMB`/`maxWidthOrHeight`
  options match this use case directly, no WASM/canvas hand-rolling of
  EXIF-orientation edge cases). **Deviation from the no-third-party-CDN
  posture** established by capa-offline's Workbox rejection — flagged
  explicitly below, not silently reintroduced.
- Offline queueing through the existing shared `offline-db.js` Dexie schema
  (single `.version()` owner) — new store/shape added there, never a second
  `Dexie(...)` instance. `paso-offline.js`'s existing `FormData` POST needs
  no rework.
- Excel embedding: template YAML gains a small fixed number of named anchor
  slots for attachments (mirrors today's scalar `celda` anchor declaration).
  `generador.py` gets a new `_incrustar_adjuntos` primitive (multi-image,
  multi-anchor) — a generalization of, not a reuse of, `_intercambiar_logo`.
- New Django view to list/download a report's attachments server-side.

### Out of Scope
- Extending `TipoDeDato` to a declarative file/image type (Approach 2) —
  disproportionate to a single MVP slot (S-08 only).
- `permite_adjunto` YAML flag for future report types (Approach 3) —
  deferred until a second attachment-bearing report type exists.
- In-place attachment replacement/cleanup — `VercelBlobStorage.exists()`
  always returns `False` (content-addressed); documented as a known
  limitation, not solved here.
- Automated JS test coverage for compression/offline/upload — no JS runner
  exists in this project; manual DevTools verification, same pattern as
  #9/#10.

## Capabilities

### New Capabilities
- `adjuntos-reporte`: attachment capture (upload, offline queue,
  client-side compression, format/size validation, per-attachment failure
  isolation) and server-side storage/listing for a `Reporte`.

### Modified Capabilities
- `generador-excel` (if such a spec exists under `openspec/specs/`) or the
  equivalent `tipos_reporte/generador.py` behavior: gains multi-image
  attachment embedding alongside the existing logo swap. (`openspec/specs/`
  is currently empty in this repo — treat as new capability surface if no
  matching spec is found at spec time.)

## Approach

Standalone `Adjunto` model (Approach 1 from exploration), isolated from the
declarative `TipoDeDato` system. Reuse `VercelBlobStorage` as-is. Client
compresses via CDN library before queueing through the shared Dexie schema;
if the CDN is unreachable (offline-first), capture proceeds with the
**uncompressed** original — compression is a best-effort optimization, never
a hard blocker, and the 8MB ceiling still applies. Server validates format/
size independently of the client (never trusts client-side compression).
Excel embedding uses a new bounded multi-anchor primitive in `generador.py`;
attachments beyond the declared anchor-slot count remain stored and listable
but are not embedded in the `.xlsx` (documented limitation, not a defect).

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/models.py` | New | `Adjunto` model + migration |
| `reportes/views.py` | Modified | Upload endpoint, list/download view |
| `reportes/urls.py` | Modified | New routes |
| `reportes/static/reportes/paso-offline.js` | Modified | Compression call, queue write |
| `reportes/static/reportes/offline-db.js` | Modified | New store/shape (same owner) |
| `reportes/templates/reportes/paso.html` | Modified | S-08 file input, CDN `<script>` |
| `tipos_reporte/generador.py` | Modified | New `_incrustar_adjuntos` primitive |
| `tipos_reporte/definicion` (YAML schema/docs) | Modified | Attachment anchor-slot declaration |
| `reportes/tests/` | Modified | New model/view/generator tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|--------------|
| CDN-loaded compression library deviates from established no-third-party-CDN posture (capa-offline precedent) | Med | Explicit, acknowledged deviation; library is optional/best-effort, never a hard capture blocker if unreachable |
| First format/size validation in this codebase — no precedent to follow | Low | Concrete allowlist (JPEG/PNG/WEBP/HEIC) + 8MB backstop ceiling, enforced client and server side |
| HEIC support requires a second CDN-loaded WASM library (`heic2any`), doubling the CDN-unreachable/failure surface and adding conversion latency before compression even starts | Med | Conversion failure is treated the same as compression-library-unreachable: fall back to the original file if it independently clears the 8MB ceiling, otherwise block only that attachment; server still re-validates format/size regardless of client outcome |
| HEIC pipeline (detect → convert → compress) is untested against real device output (HEIC variants differ by iOS version/camera settings) | Med | Manual DevTools verification against a real iPhone-captured HEIC file before merge, same pattern as other JS-untestable paths |
| Excel anchor-slot count may not match real-world attachment volume | Med | Overflow attachments stay server-accessible, not silently dropped; documented, not a blocker |
| No automated JS test coverage | Med | Manual DevTools checklist, same as #9/#10 |
| `VercelBlobStorage.exists()` always `False` → no cleanup on delete/replace | Low | Documented known limitation, out of scope |

## Rollback Plan

All additive: drop the `Adjunto` model/migration, remove the upload/list
views and routes, revert `paso.html`/`paso-offline.js`/`offline-db.js`
changes, and remove `_incrustar_adjuntos` from `generador.py` (logo-only
behavior is unaffected since it's a separate function). No existing model
or endpoint is altered destructively.

## Dependencies

- `browser-image-compression` (CDN, no local install) — new third-party CDN
  dependency, flagged as a deviation above.
- `heic2any` (CDN, no local install) — second new third-party CDN
  dependency, required only for HEIC→JPEG pre-conversion; same deviation,
  compounded (two CDN libraries in the offline-capture path instead of one).
- Backlog #9 (capa-offline) — provides the shared Dexie schema this reuses.
  Already merged.

## Success Criteria

- [ ] A user can attach a photo to S-08; oversized/unsupported files block
      only that attachment, never the rest of the step submission.
- [ ] Attachments compress client-side before upload when the CDN library
      loads; capture still succeeds (uncompressed, ceiling-checked) when it
      does not.
- [ ] Attachments queue and sync offline through the shared Dexie schema,
      with no second `Dexie(...)` instance introduced.
- [ ] The generated `.xlsx` embeds attachments up to the declared anchor-slot
      count; overflow attachments remain listable/downloadable server-side.
- [ ] Format/size validation runs identically on client and server, and
      includes HEIC/HEIF alongside JPEG/PNG/WEBP.
- [ ] A HEIC file (e.g. from an iPhone camera) is converted to JPEG
      client-side before compression, or — if conversion fails/is
      unreachable — falls back to the original file under the 8MB ceiling
      without blocking the rest of the step.

## Proposal question round — resolved

All three open judgment calls from the prior round are now confirmed by the
user; no further product decisions are open for this proposal:

1. **Excel anchor-slot count**: confirmed at 4 (assumption unchanged).
2. **Format allowlist**: changed — HEIC/HEIF MUST be accepted (not just
   JPEG/PNG/WEBP), since it is the default capture format on iPhone
   cameras. Since HEIC has no native decode path in Chrome/Firefox
   `<canvas>` (and `browser-image-compression` itself does not decode
   HEIC), this proposal adds `heic2any` as a second CDN-loaded library to
   convert HEIC→JPEG before the existing compression pass. This compounds
   the CDN-dependency deviation already flagged for compression (two CDN
   libraries in the offline-capture path instead of one) — see Risks and
   Dependencies above for the explicit cost/fallback behavior.
3. **Attachment count cap**: confirmed — no hard cap on stored attachments
   per report; only Excel embedding is capped at the 4 anchor slots
   (assumption unchanged).
