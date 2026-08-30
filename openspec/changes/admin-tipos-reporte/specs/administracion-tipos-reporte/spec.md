# Administración de Tipos de Reporte Specification

## Purpose

Give administrators a dedicated, role-gated screen to list, view, create,
edit, activate, and desactivate `TipoDeReporte`/`DefinicionDeTipo` records,
replacing Django admin as the management surface for these two models
(backlog #13, S-14). `tipos_reporte/servicios.py`'s existing
`activar_definicion`/`desactivar_tipo` and `tipos_reporte/validacion.py`'s
existing validation rules are reused unchanged; this capability adds only
the screen, forms, access-control gate, and a shared YAML-parsing helper
extracted from `admin.py`.

## Requirements

### Requirement: Admin-Role-Gated Access

The system MUST restrict every view in this capability (list, detail,
create, edit, activate, desactivate) to authenticated users for whom
`Usuario.es_administrador` is `True`. A new decorator reusing
`Usuario.es_administrador` MUST be the single gating mechanism applied to
all of these views. An authenticated non-administrator MUST receive a
403 Forbidden response; the view MUST NOT execute its normal body or
expose any `TipoDeReporte`/`DefinicionDeTipo` data. An anonymous user MUST
be redirected to the login flow, consistent with `@login_required`.

#### Scenario: Administrator reaches the list view

- GIVEN an authenticated user with `rol=Rol.ADMINISTRADOR`
  (`es_administrador` is `True`)
- WHEN that user requests the tipos de reporte list view
- THEN the view executes normally and returns the list of
  `TipoDeReporte` rows

#### Scenario: Non-administrator is blocked with 403

- GIVEN an authenticated user with `rol` other than `ADMINISTRADOR`
  (`es_administrador` is `False`)
- WHEN that user requests any view in this capability (list, detail,
  create, edit, activate, desactivate)
- THEN the response is 403 Forbidden and no `TipoDeReporte`/
  `DefinicionDeTipo` data is returned

#### Scenario: Anonymous user is redirected to login

- GIVEN no authenticated session
- WHEN a request is made to any view in this capability
- THEN the user is redirected to the login flow

### Requirement: List View With Search and Pagination

The system MUST provide a list view of `TipoDeReporte` rows following the
same list/search/pagination pattern established by
`reportes/listado.py` + `Paginator.get_page()` (backlog #12's
`mis_reportes` precedent): pure query helper(s) composed with Django's
`Paginator`, paginated results, and an optional `?q=` search parameter.
The list MUST be reachable only by administrators (per the Admin-Role-Gated
Access requirement).

#### Scenario: List paginates results

- GIVEN more `TipoDeReporte` rows exist than fit on one page
- WHEN an administrator requests the list view
- THEN the response includes only one page of results plus pagination
  metadata/controls to reach subsequent pages

#### Scenario: List supports search

- GIVEN `TipoDeReporte` rows with distinct `nombre`/`codigo` values
- WHEN an administrator requests the list view with a `?q=` parameter
  matching one row's `nombre` or `codigo`
- THEN only matching rows are returned

### Requirement: Detail View

The system MUST provide a detail view for a single `TipoDeReporte`,
showing its fields (`nombre`, `codigo`, `version_formato`, `logo`,
`plantilla`, `definicion_activa`) and its related `DefinicionDeTipo`
history (state, version, `activada_en`), reachable only by administrators.

#### Scenario: Administrator views tipo detail

- GIVEN a `TipoDeReporte` with an active `DefinicionDeTipo` and at least
  one historical `DefinicionDeTipo`
- WHEN an administrator requests its detail view
- THEN the response shows the tipo's fields and both the active and
  historical definiciones

### Requirement: Activation Reuses Existing Service Unchanged

The system MUST call `tipos_reporte/servicios.py::activar_definicion`
exactly as it exists today (zero changes to that function) to activate a
`DefinicionDeTipo` from the new screen. The screen MUST surface the
returned `ResultadoDeValidacion`: on success, confirm the activation; on
failure, display every accumulated `ProblemaDeDefinicion` (`ubicacion` +
`mensaje`), matching `admin.py`'s existing per-problem message behavior.

#### Scenario: Activation succeeds through the new screen

- GIVEN a `borrador` `DefinicionDeTipo` whose `estructura` validates
  cleanly against its tipo's `plantilla`
- WHEN an administrator triggers activation from the new screen
- THEN `activar_definicion` runs, the definición transitions to `activa`,
  and the screen confirms success

#### Scenario: Activation failure surfaces every problem

- GIVEN a `borrador` `DefinicionDeTipo` whose `estructura` fails multiple
  validation rules against its tipo's `plantilla`
- WHEN an administrator triggers activation from the new screen
- THEN the definición remains `borrador` (no partial state change) and
  the screen displays every accumulated problem returned by
  `activar_definicion`

### Requirement: Desactivation Reuses Existing Service Unchanged

The system MUST call `tipos_reporte/servicios.py::desactivar_tipo`
exactly as it exists today (zero changes to that function) to desactivate
a `TipoDeReporte` from the new screen.

#### Scenario: Desactivation succeeds through the new screen

- GIVEN a `TipoDeReporte` with an active `DefinicionDeTipo`
- WHEN an administrator triggers desactivation from the new screen
- THEN `desactivar_tipo` runs, `definicion_activa` is cleared, the former
  active definición moves to `historica`, and its `version` is unchanged

### Requirement: Create and Edit Forms for TipoDeReporte

The system MUST provide create and edit forms for `TipoDeReporte`
covering `nombre`, `codigo`, `version_formato`, `logo`, and `plantilla`,
reachable only by administrators.

#### Scenario: Administrator creates a new TipoDeReporte

- GIVEN an administrator on the create form
- WHEN they submit valid `nombre`, `codigo`, and `plantilla` (an `.xlsx`
  file)
- THEN a new `TipoDeReporte` row is created with no active
  `DefinicionDeTipo`

### Requirement: Logo Edit Without Re-Upload Keeps Existing Logo

The system MUST NOT clear or replace a `TipoDeReporte`'s `logo` when an
administrator submits the edit form without selecting a new logo file.
This MUST replicate Django's default `ModelForm`/`ClearableFileInput`
behavior already relied upon at the form level, and MUST NOT regress
`tipos_reporte/generador.py::_intercambiar_logo`'s existing
generation-time behavior: when `TipoDeReporte.logo` is empty, the `.xlsx`
template's own embedded logo is left untouched (no logo is inserted, no
existing template image is removed).

#### Scenario: Editing without re-uploading keeps the existing logo

- GIVEN a `TipoDeReporte` with an existing `logo` file
- WHEN an administrator submits the edit form with every field unchanged
  and no new file selected for `logo`
- THEN the `TipoDeReporte`'s `logo` field still references the original
  file after save

#### Scenario: Generation with no logo leaves the template default untouched

- GIVEN a `TipoDeReporte` with `logo` empty and a template whose sheet
  contains its own embedded image
- WHEN a report of that tipo is generated
- THEN `_intercambiar_logo` performs no swap and the template's original
  embedded image remains in the generated document, unchanged from before
  this capability existed

### Requirement: Plantilla Stays Read-Only Once a Definition Is Active

The system MUST prevent editing a `TipoDeReporte`'s `plantilla` field
through the new edit form once that tipo has an active `DefinicionDeTipo`
(`definicion_activa_id is not None`), replicating
`admin.py::TipoDeReporteAdmin.get_readonly_fields`'s existing guard. The
form MUST render `plantilla` as read-only (not merely reject a changed
value after the fact) whenever the tipo being edited has an active
definición, and MUST allow editing `plantilla` freely when the tipo has
no active definición.

#### Scenario: Plantilla is read-only when a definition is active

- GIVEN a `TipoDeReporte` with `definicion_activa` set
- WHEN an administrator opens its edit form
- THEN the `plantilla` field is rendered read-only and any submitted
  change to it is not persisted

#### Scenario: Plantilla is editable when no definition is active

- GIVEN a `TipoDeReporte` with `definicion_activa` unset (`None`)
- WHEN an administrator opens its edit form and submits a new
  `plantilla` file
- THEN the new file is persisted to the `plantilla` field

### Requirement: Create and Edit Form for DefinicionDeTipo

The system MUST provide create and edit forms for `DefinicionDeTipo`
covering `archivo_yaml` (the tipo it belongs to is fixed by context, e.g.
the URL/parent detail view), reachable only by administrators. The form
MUST derive `yaml_fuente` and `estructura` from the uploaded
`archivo_yaml` at save time via the shared YAML-validation helper (see
the Shared YAML-Validation Helper requirement below), matching
`admin.py::DefinicionDeTipoForm.clean()`'s existing derivation behavior:
`yaml_fuente`/`estructura` are never entered by hand.

#### Scenario: Administrator uploads a new definición draft

- GIVEN an administrator on the create form for a `DefinicionDeTipo`
  under an existing `TipoDeReporte`
- WHEN they submit a `.yaml` file that parses to a UTF-8-decodable,
  JSON-representable mapping
- THEN a new `borrador` `DefinicionDeTipo` is created with `yaml_fuente`
  and `estructura` populated from the uploaded file, and `estado`,
  `version`, `activada_en` are not administrator-editable

### Requirement: Shared YAML-Validation Helper

The system MUST extract the YAML-parsing/structural-validation logic
currently duplicated only inside `admin.py`'s `DefinicionDeTipoForm.clean()`
(UTF-8 decode check, `analizar_yaml_seguro` parse, dict-root check,
JSON-representability check) into one shared, non-duplicated helper
function, callable from both the new `DefinicionDeTipo` form and any
remaining call site. Both the new form and `admin.py` (only until PR2
removes its registration) MUST call this same function; the parsing/
structural-validation logic MUST NOT be reimplemented or copy-pasted in
the new form.

#### Scenario: New form and admin.py use the identical helper

- GIVEN the shared YAML-validation helper exists
- WHEN either the new `DefinicionDeTipo` form or `admin.py`'s form
  processes an uploaded `archivo_yaml`
- THEN both invoke the same shared function to decode, parse, and
  structurally validate the file — no separate implementation exists in
  either call site

#### Scenario: Non-UTF-8 file is rejected with a field error

- GIVEN an uploaded `archivo_yaml` file that is not valid UTF-8 text
- WHEN the create/edit form is submitted
- THEN the form rejects the submission with an `archivo_yaml` field error
  and no `DefinicionDeTipo` row is created or modified

#### Scenario: Non-mapping YAML root is rejected

- GIVEN an uploaded `archivo_yaml` file that parses to a YAML list or
  scalar instead of a mapping
- WHEN the create/edit form is submitted
- THEN the form rejects the submission with an `archivo_yaml` field error
  stating the document must be a mapping at its root

### Requirement: Django Admin Registration Removed After Replacement Ships

The system MUST remove `@admin.register` for both `TipoDeReporte` and
`DefinicionDeTipo` from `tipos_reporte/admin.py` only once the new
create/edit screen (list/detail/activate/desactivate plus create/edit) is
available, so there is never a window where neither Django admin nor the
new screen can create a `DefinicionDeTipo`. This removal MUST NOT happen
before the new create/edit forms ship.

#### Scenario: Admin registration removed once new create/edit screen exists

- GIVEN the new screen's create/edit forms for `TipoDeReporte` and
  `DefinicionDeTipo` are deployed and reachable by administrators
- WHEN `tipos_reporte/admin.py` is inspected
- THEN `TipoDeReporte` and `DefinicionDeTipo` are no longer registered
  with Django admin (`@admin.register` removed for both)

### Requirement: No Size or Format Ceiling on Logo, Plantilla, or Archivo YAML Uploads

The system MUST NOT impose any file size or format/content-type
validation on `logo`, `plantilla`, or `archivo_yaml` uploads in this
capability beyond what Django's `ImageField`/`FileField` already enforce
(e.g. `ImageField`'s built-in image-decodability check). This is a
deliberate, documented scope decision — these are trusted-administrator
uploads, unlike `reportes/adjuntos.py`'s end-user-facing `Adjunto`
uploads (backlog #11), which do enforce size/format limits. This
capability MUST NOT silently add such limits without an explicit,
separate change.

#### Scenario: Oversized plantilla is accepted

- GIVEN an administrator submits a `.xlsx` `plantilla` file larger than
  any size ceiling applied elsewhere in this codebase (e.g. larger than
  `Adjunto`'s upload limit)
- WHEN the create/edit form is submitted with an otherwise-valid file
- THEN the form does not reject the submission for file size

### Requirement: Delete UI Explicitly Out of Scope

The system MUST NOT provide a delete action for `TipoDeReporte` or
`DefinicionDeTipo` in this capability, including for never-activated
drafts. This is a documented known limitation, not a silent omission:
Django admin's previously-available guarded delete action is not
replicated by this capability. Model- and QuerySet-level delete guards
(`models.py`) remain unaffected and continue to block hard-delete of any
row that was ever activated.

#### Scenario: No delete action is offered anywhere in the new screen

- GIVEN an administrator viewing the list or detail view for a
  never-activated (`borrador`) `DefinicionDeTipo`
- WHEN they look for a delete action in this capability's views
- THEN no delete action is present; removing the row (if ever needed)
  requires direct database/shell access outside this capability

### Requirement: PPI Shotcrete Configuration Exercise Explicitly Out of Scope

The system's "a new report type can be added through configuration alone"
claim MUST NOT be exercised or verified against a second real report
format (e.g. PPI Shotcrete) as part of this capability. This is a
documented known limitation: no sample YAML/plantilla data for a second
type exists in the repository, and creating one is tracked as separate,
future work.

#### Scenario: No second-type acceptance data ships with this capability

- GIVEN this capability's PR1/PR2 are both merged
- WHEN the repository is inspected for a second report type's sample
  YAML/plantilla
- THEN none exists; the only exercised `DefinicionDeTipo` content remains
  whatever existed before this capability

### Requirement: Blob Storage Replacement Cleanup Explicitly Out of Scope

The system MUST NOT attempt any in-place replacement or cleanup of a
previously-uploaded `logo`, `plantilla`, or `archivo_yaml` blob when a
new file is uploaded to the same field. This is a known, pre-existing
limitation of `config/storage.py::VercelBlobStorage`, whose `exists()`
method always returns `False` (content-addressed storage, no in-place
replacement semantics), and is not solved by this capability.

#### Scenario: Re-uploading a plantilla does not remove the prior blob

- GIVEN a `TipoDeReporte` whose `plantilla` was previously uploaded to
  blob storage
- WHEN an administrator uploads a new `plantilla` file (tipo has no
  active definición, so the field is editable)
- THEN the new file is stored and referenced by the `plantilla` field,
  and the prior file's blob is not deleted or otherwise cleaned up by
  this capability
