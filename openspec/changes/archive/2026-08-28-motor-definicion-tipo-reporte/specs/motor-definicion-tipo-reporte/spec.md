# tipos_reporte Specification

> Engram: `sdd/motor-definicion-tipo-reporte/spec` (observation #73)
> Proposal: `sdd/motor-definicion-tipo-reporte/proposal` (observation #72)
> Related ADRs: ADR-0002 (empirical template findings), ADR-0003 (modelo de datos y plantillas), ADR-0008 (fallo limpio y validacion anticipada)

> Revision 2 amendment. The design (Engram #74) was produced in parallel with
> this spec, before the spec existed, and flagged two additions as [needs-spec]:
> a mandatory hoja key in the YAML definition (design D6), justified by ADR-0002 s
> empirical finding that the reference workbook carries a second, hidden report
> format sharing the same file; and the MEDIA_ROOT/MEDIA_URL/Pillow prerequisite
> (design D10) that this items first FileField/ImageField usage requires locally
> and in tests. This revision adds the "Definition names its sheet" requirement
> and its two scenarios, and the "Local file storage for uploads" requirement and
> its two scenarios, and updates Dependencies accordingly.

## Purpose

Defines the tipos_reporte app: TipoDeReporte and DefinicionDeTipo models, YAML-to-JSONField declarative definition loading, and the exhaustive activation-time validator required by ADR-0003 and ADR-0008.

## Out of Scope

- Real .xlsx generation (backlog item #4).
- Capture wizard / form rendering (backlog item #5).
- Custom admin UI (backlog item #13); stock Django ModelAdmin is used.
- ValorDeReporte, Reporte, and other capture/report entities (items #4/#5 onward).
- Self-service creation of report types from a non-admin interface.
- Field/item-level role permissions (roles key is Excel-column metadata only).
- Production storage (Vercel Blob, item #11).

## Requirements (condensed; see Engram #73 for full scenario text)

### Requirement: TipoDeReporte model
Fields: nombre, unique codigo, version, optional logo image, required plantilla (.xlsx), activo status, timestamps. Created inactive by default. codigo uniqueness enforced.

### Requirement: DefinicionDeTipo model and YAML loading
Stores archivo_yaml, yaml_fuente, and normalized estructura JSONField. Uploading and saving through the admin MUST parse with PyYAML and populate the JSONField. Malformed YAML rejected at save time with an actionable error; nothing partially persisted.

### Requirement: Definition names its sheet (revision 2 addition)
The definition MUST declare hoja (required key, not an inferred default). Activation MUST reject a definition whose declared hoja does not exist in the template.

### Requirement: Versioning - edit requires deactivation first
Editing a DefinicionDeTipo in place while its TipoDeReporte is activo is blocked. Each successful activation produces an immutable version. Deactivating makes the definition editable again; a later activation increments version.

### Requirement: Closed data-type catalog
Exactly: texto, numero, fecha, hora, seleccion, booleano, rango-hora-inicio-fin. Anything outside this set is rejected.

### Requirement: Exhaustive activation validation (accumulate all errors)
R1 required structural fields; R2 known data type; R3 valid cell notation; R4 no cell collisions; R5 template/sheet readable; R6 every destination cell is a merge anchor. All problems accumulated in one pass, never stop-at-first-error. On any failure, TipoDeReporte MUST remain in its prior state (no partial mutation).

### Requirement: Deletion blocked after any successful activation
Physical deletion of a TipoDeReporte or DefinicionDeTipo is blocked from the admin once ever activated, regardless of current activo status. Deactivation remains available. Never-activated rows may be deleted.

### Requirement: Django admin integration for definition and activation
TipoDeReporte and DefinicionDeTipo registered in the stock Django admin. An administrator uploads a template, uploads a YAML definition, and triggers activation (e.g. an admin action). The validator runs synchronously; the response shows the activated state or the full accumulated error list.

### Requirement: Extending with a second report type requires no code change
Defining and activating a second, structurally different TipoDeReporte MUST NOT require any change to the validator or the models.

### Requirement: Local file storage for uploads (revision 2 addition)
plantilla and logo MUST be storable/servable on the local filesystem in dev and tests. An uploaded template is written to local storage and readable back (e.g. by openpyxl). An uploaded logo image is validated and persisted; a non-image file uploaded as logo MUST be rejected as an invalid image.

## Dependencies
- PyYAML, openpyxl, Pillow added to requirements.txt.
- MEDIA_ROOT/MEDIA_URL configured for local/test storage.
- Depends on backlog item #1 (Usuario/rol) for admin-gated access.

## Dependency Note
tipos_reporte/DefinicionDeTipo.estructura (JSONField) is the sole source of truth items #4/#5 must read from. Production storage (Vercel Blob) belongs to item #11.

---
Full verbatim text (all requirement/scenario Given/When/Then wording) is preserved in Engram observation #73 and was verified word-for-word against this condensation during sdd-verify.
