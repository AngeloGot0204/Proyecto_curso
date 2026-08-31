# Proposal: Administración de tipos de reporte (S-14, backlog #13)

## Intent

`TipoDeReporte`/`DefinicionDeTipo` CRUD exists only through Django admin
(backlog #3, archived) — no dedicated screen, and admin's generic
changelist/change-form UX was never meant to carry activation workflows,
guarded readonly fields, and untrusted-YAML upload validation as a primary
product surface. This change gives administrators a purpose-built screen for
managing report types, replacing Django admin access to these two models
entirely, and extracts the YAML-parsing validation used by both the old
admin form and the new screen into one shared, non-duplicated helper.

## Scope

### In Scope
- New `tipos_reporte` views/urls/templates: list (search + pagination,
  `listado.py`/`mis_reportes` pattern), detail, activate (`servicios.py::
  activar_definicion`, reused unchanged), desactivate (`servicios.py::
  desactivar_tipo`, reused unchanged).
- New create/edit forms for `TipoDeReporte` (logo, plantilla) and
  `DefinicionDeTipo` (archivo_yaml), replicating the existing
  `plantilla`-readonly-once-active guard and the existing logo-keep-on-no-
  reupload form behavior — neither is rebuilt, both are preserved.
- Shared YAML-parsing/validation helper (`analizar_yaml_seguro` +
  structural checks currently in `admin.py`'s `DefinicionDeTipoForm.clean()`)
  moved into `tipos_reporte/validacion.py` (or `servicios.py`, whichever fits
  best once written), called by the new form. Single implementation, no
  duplication.
- New admin-role gate reusing `Usuario.es_administrador`, added as a
  decorator (e.g. `usuarios/decorators.py`).
- `tipos_reporte/admin.py` `@admin.register` removed for `TipoDeReporte` and
  `DefinicionDeTipo` once the new create/edit screen (PR 2) ships — the
  dedicated screen becomes the only management surface.
- Delivered as 2 chained PRs, same stacked pattern as #10/#11/#12: PR 1 =
  list/detail/activate/desactivate; PR 2 = create/edit forms with
  logo/plantilla/archivo_yaml upload, validation, and the admin.py removal.
- No size/format ceilings on logo/plantilla/archivo_yaml uploads — deliberate
  scope decision, not an oversight: these are trusted-admin uploads, unlike
  backlog #11's end-user-facing `Adjunto` uploads, which do have limits.

### Out of Scope
- Configuring a second report type (e.g. PPI Shotcrete) as an acceptance
  exercise — the "new type = configuration only" claim stays unexercised by
  this change; tracked as a known limitation/follow-up.
- Any change to `servicios.py`/`validacion.py` business logic beyond the
  YAML-helper extraction — both are already UI-agnostic and reused as-is.
- Size/format validation for these three uploads (see In Scope above).
- Delete UI for never-activated drafts. Admin previously offered a
  guarded delete action; the new screen does not replicate it. Documented
  limitation, not silently dropped — see Risks.
- Any in-place replacement/cleanup of superseded blobs
  (`VercelBlobStorage.exists()` always returns `False`) — known limitation.

## Capabilities

### New Capabilities
- `administracion-tipos-reporte`: dedicated admin-role-gated screen for
  `TipoDeReporte`/`DefinicionDeTipo` list/detail/create/edit/activate/
  desactivate, replacing Django admin access to these models.

### Modified Capabilities
- None.

## Approach

Thin screen wrapping existing services (exploration Approach 2), split per
Approach 4 to respect the review-budget guard: PR 1 covers everything
read-oriented plus the two existing state-transition services (zero new
business logic, list pattern copied from `listado.py`); PR 2 adds the
upload/validation surface (new forms, shared YAML helper, admin-role
decorator) and retires `admin.py`'s registrations for these two models only
once the replacement is live, avoiding any gap where neither surface can
create a new definition.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `tipos_reporte/views.py`, `urls.py`, `templates/tipos_reporte/` | New | List/detail/activate/desactivate (PR1), create/edit (PR2) |
| `tipos_reporte/forms.py` | New | Upload forms, calls shared YAML helper |
| `tipos_reporte/validacion.py` (or `servicios.py`) | Modified | Shared YAML-parsing helper extracted from `admin.py` |
| `tipos_reporte/admin.py` | Modified | `@admin.register` removed for both models (PR2) |
| `usuarios/decorators.py` | New | Admin-role gate on `Usuario.es_administrador` |
| `tipos_reporte/servicios.py` | Unchanged | Reused as-is |
| `tipos_reporte/tests/` | Modified | New view/form/decorator tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|--------------|
| No delete UI for never-activated drafts once admin access is removed | Low | Documented known limitation; drafts are inert until activated, so a stray unusable draft has no functional impact — direct DB/shell cleanup remains available to maintainers |
| No format/size validator precedent for these three fields | Low | Explicit deliberate no-limit decision (trusted admins), documented, not silently omitted |
| Duplicated YAML-parsing logic if extraction is skipped or done loosely | Low | Extraction is in scope for PR2, single call site in the new form after `admin.py` registrations are removed |
| Admin-role decorator has no precedent in this codebase | Low | New decorator reuses existing `Usuario.es_administrador`, mirrors `@login_required` usage already established |
| PPI Shotcrete "new type = configuration only" claim remains unverified | Low | Explicit known limitation, tracked as future backlog work |

## Rollback Plan

All additive except the `admin.py` registration removal in PR2, which is a
one-line-per-model revert (`@admin.register(...)` restored) if the new
screen needs to be pulled. PR 1 rollback removes new views/urls/templates
only, admin remains available throughout. No migrations are introduced.

## Dependencies

- Backlog #3 (`tipos_reporte` admin, archived) — provides `servicios.py`/
  `validacion.py`, reused unchanged.
- Backlog #12 (`mis-reportes`, archived) — provides the list/pagination
  pattern (`listado.py`) this change follows.
- Backlog #11 (`adjuntos`, archived) — contrast precedent for the
  deliberate no-size/format-limit decision on these uploads.

## Success Criteria

- [ ] An administrator can list, view, create, edit, activate, and
      desactivate `TipoDeReporte`/`DefinicionDeTipo` entirely from the new
      screen, without Django admin.
- [ ] Non-administrators cannot reach the new screen's views.
- [ ] Editing a `TipoDeReporte` without re-uploading a logo keeps the
      existing one; `plantilla` stays readonly once a definition is active.
- [ ] YAML parsing/validation runs through exactly one shared helper, called
      by the new form (and by `admin.py` only until PR2 removes it).
- [ ] `@admin.register` for `TipoDeReporte`/`DefinicionDeTipo` is removed
      once PR2 ships.

## Proposal question round — assumptions for review

Two sequencing/scope calls were not explicit in the 5 resolved decisions and
were resolved here with a reasonable default; flag if either should change:

1. **`admin.py` removal timing**: assumed to happen in PR2 (once the
   replacement create/edit screen exists), not PR1 — removing it earlier
   would leave a window with no way to create a new `DefinicionDeTipo` at
   all. If you'd rather remove admin access immediately in PR1 and accept
   that gap, say so.
2. **Delete UI for never-activated drafts**: admin's existing guarded
   delete action is not replicated in the new screen (backlog #13 lists
   list/detail/activate/desactivate + create/edit, not delete). Assumed
   acceptable since drafts are inert. If drafts need a delete action, this
   should be added to PR1 or PR2 scope.
