# Verify Report: admin-tipos-reporte

## Change
admin-tipos-reporte (backlog #13, S-14). Delivered across 4 commits on main
(stacked-to-main, plus 2 follow-up bugfixes found during manual browser
verification):
- `3fe8907` feat(tipos_reporte): agrega pantalla de solo lectura y activacion (PR1)
- `5d92b9f` feat(tipos_reporte): agrega formularios de creacion/edicion, quita Django admin (PR2)
- `b5ebcd2` fix(tipos_reporte): agrega links de navegacion a crear/editar
- `084459c` fix(tipos_reporte): excluye plantilla del form en vez de disabled=True

## Mode
Full artifact set (proposal, one spec, design, tasks). Full verification
performed: completeness, correctness, coherence, plus real test execution.

Note on requirement/scenario count: the task brief stated "13 requirements".
The retrieved spec file
(openspec/changes/admin-tipos-reporte/specs/administracion-tipos-reporte/spec.md)
actually contains 15 requirements and 23 scenarios (verified by direct
grep count of "### Requirement:" and "#### Scenario:" headers). This report
uses the real, counted totals (15/23), per the rule that envelope totals
must be counted from the artifact, never assumed.

## Task Completeness

77/77 tasks checked across 8 phases (Phase 1 Decorator, Phase 2 Listado,
Phase 3 List/Detail/Activate/Desactivate views, Phase 4 PR1 Verification,
Phase 5 YAML Helper Extraction, Phase 6 Forms, Phase 7 Create/Edit Views,
Phase 8 Admin Deregistration + Regression + Full Suite). 0 unchecked. No
CRITICAL from task completeness.

Task-text staleness (not a functional gap, flagged under Correctness Issues
below): tasks 6.1 and 6.6's literal text still say
plantilla_disabled_true_... / self.fields["plantilla"].disabled = True
-- the actual shipped test is named
test_tipo_de_reporte_form_plantilla_excluida_con_definicion_activa and the
actual shipped code uses del self.fields["plantilla"], per the later
revision. The checked box is correct (the intent -- plantilla becomes
unmodifiable once active -- is satisfied) but the task's literal prose was
never updated to match the revision.

## Test Execution Evidence

Command run directly in this verification pass (not trusted from prior
claims), against the real Neon Postgres test DB, in isolation (single
process, no -n/xdist):

| Command | Result | Time |
|---|---|---|
| .venv/Scripts/python.exe -m pytest -p no:xdist -q (full repo suite) | 369 passed, 0 failed, 0 errors, exit 0 | 785.78s (0:13:05) |

This independently reproduces the apply-progress claim of "349 passed" for
the tipos_reporte/ usuarios/ reportes/ combined suite (that number was
scoped to 3 apps; 369 is the full-repo total, a superset that includes
other apps' suites) -- no regressions found anywhere in the repository.

## Spec Compliance Matrix

### administracion-tipos-reporte (15 requirements, 23 scenarios -- all PASS)

| Requirement / Scenario | Status | Evidence |
|---|---|---|
| Admin-Role-Gated Access - Administrator reaches the list view | PASS | test_solo_administradores_permite_administrador, test_lista_pagina_1_tiene_20_y_pagina_2_tiene_1 |
| Admin-Role-Gated Access - Non-administrator is blocked with 403 | PASS | test_solo_administradores_bloquea_no_administrador_403, test_lista_no_administrador_403_sin_datos (also asserts no codigo leaked), test_detalle_no_administrador_403, test_crear_tipo_no_administrador_403 |
| Admin-Role-Gated Access - Anonymous user is redirected to login | PASS | test_solo_administradores_anonimo_redirige_antes_de_leer_rol (no-DB, proves property never read), test_lista_anonimo_redirige_login |
| List View With Search and Pagination - List paginates results | PASS | test_lista_pagina_1_tiene_20_y_pagina_2_tiene_1 (21 rows, 20/1 split), test_lista_page_param_invalido_no_falla |
| List View With Search and Pagination - List supports search | PASS | test_lista_busqueda_por_q, test_aplicar_busqueda_por_nombre, test_aplicar_busqueda_por_codigo, test_aplicar_busqueda_ignora_acentos |
| Detail View - Administrator views tipo detail | PASS | test_detalle_muestra_definicion_activa_e_historicas |
| Activation Reuses Existing Service Unchanged - Activation succeeds | PASS | test_activar_definicion_exito_mensaje_success_y_estado_activa |
| Activation Reuses Existing Service Unchanged - Activation failure surfaces every problem | PASS | test_activar_definicion_falla_muestra_todos_los_problemas_y_permanece_borrador (2+ messages, stays borrador) |
| Desactivation Reuses Existing Service Unchanged - Desactivation succeeds | PASS | test_desactivar_tipo_exito_limpia_definicion_activa_y_version_sin_cambios |
| Create and Edit Forms for TipoDeReporte - Administrator creates a new TipoDeReporte | PASS | test_crear_tipo_administrador_exito_sin_definicion_activa |
| Logo Edit Without Re-Upload Keeps Existing Logo - Editing without re-uploading keeps the existing logo | PASS | test_editar_tipo_sin_reupload_logo_mantiene_logo_existente |
| Logo Edit Without Re-Upload Keeps Existing Logo - Generation with no logo leaves the template default untouched | PASS | test_intercambiar_logo_logo_vacio_deja_imagen_de_plantilla_intacta |
| Plantilla Stays Read-Only Once a Definition Is Active - Plantilla is read-only when a definition is active | PASS | test_tipo_de_reporte_form_plantilla_excluida_con_definicion_activa, test_tipo_de_reporte_form_plantilla_posteada_en_tipo_activo_no_persiste, test_editar_tipo_plantilla_solo_lectura_cuando_definicion_activa_no_persiste_cambio |
| Plantilla Stays Read-Only Once a Definition Is Active - Plantilla is editable when no definition is active | PASS | test_tipo_de_reporte_form_plantilla_editable_sin_definicion_activa |
| Create and Edit Form for DefinicionDeTipo - Administrator uploads a new definicion draft | PASS | test_definicion_de_tipo_form_yaml_valido_crea_borrador_con_yaml_fuente_y_estructura_derivados, test_crear_definicion_yaml_valido_crea_borrador_bajo_tipo_de_url |
| Shared YAML-Validation Helper - New form and admin.py use the identical helper | PASS | tipos_reporte/forms.py and tipos_reporte/admin.py both import/call analizar_definicion_subida - single implementation confirmed by source inspection; test_admin.py's 16 tests unmodified and green |
| Shared YAML-Validation Helper - Non-UTF-8 file is rejected with a field error | PASS | test_analizar_definicion_subida_no_utf8_lanza_validation_error_archivo_yaml |
| Shared YAML-Validation Helper - Non-mapping YAML root is rejected | PASS | test_analizar_definicion_subida_raiz_lista_rechazada, test_analizar_definicion_subida_raiz_escalar_rechazada |
| Django Admin Registration Removed After Replacement Ships - Admin registration removed once new create/edit screen exists | PASS | test_admin_registry_no_contiene_tipo_de_reporte_ni_definicion_de_tipo |
| No Size or Format Ceiling - Oversized plantilla is accepted | PASS | test_crear_o_editar_plantilla_oversize_es_aceptada |
| Delete UI Explicitly Out of Scope - No delete action is offered anywhere in the new screen | PASS | Source inspection: lista.html/detalle.html/formulario_tipo.html/formulario_definicion.html contain no delete form/route; tipos_reporte/urls.py defines no delete route |
| PPI Shotcrete Configuration Exercise Explicitly Out of Scope - No second-type acceptance data ships | PASS | Source inspection: no second sample YAML/plantilla added by this change's diff |
| Blob Storage Replacement Cleanup Explicitly Out of Scope - Re-uploading a plantilla does not remove the prior blob | PASS | Source inspection: TipoDeReporteForm/config/storage.py::VercelBlobStorage unchanged by this capability; no cleanup logic added |

23/23 scenarios PASS with a runtime-passing covering test, except the 3
out-of-scope-confirmation scenarios (Delete UI, PPI Shotcrete, Blob Cleanup)
which are inherently "prove an absence" scenarios verified by source
inspection rather than a dedicated runtime assertion -- consistent with how
this project's prior verify reports (e.g. mis-reportes) treat negative/
absence-proving scenarios. No UNTESTED or FAILING scenarios.

## Design Coherence (D1-D8)

| Decision | Implemented as designed |
|---|---|
| D1, solo_administradores with login_required applied outermost, single gating mechanism, shipped in PR1 (Open Question resolved) | Yes, exact match. usuarios/decorators.py confirmed: login_required(_envoltura) wraps a PermissionDenied check; @wraps used; no per-view inline duplicate guard found in views.py. Shipped in PR1 commit 3fe8907 as the Open Question resolution required |
| D2, shared YAML helper in validacion.py, admin.py becomes a one-line call site | Yes, exact match. analizar_definicion_subida lives in tipos_reporte/validacion.py; admin.py::DefinicionDeTipoForm.clean() calls it in one line with a comment naming the shared helper; tipos_reporte/forms.py::DefinicionDeTipoForm.clean() calls the same function - single implementation confirmed |
| D3, list view copies backlog #12's pattern, _sin_acentos duplicated with a comment naming its twin | Yes, exact match. tipos_reporte/listado.py confirmed: TAMANO_DE_PAGINA in views.py (not listado.py, consistent with #12's split), ("nombre", "id") ordering, select_related("definicion_activa"), no reportes import |
| D4, plantilla read-only guard on the form | Deviation found - see below. design.md's D4 section still documents disabled=True; shipped code (forms.py, commit 084459c) uses del self.fields["plantilla"] (field exclusion). Functionally equivalent (spec's "render read-only, not merely reject after the fact" is satisfied either way - the field disappears from the rendered form and ModelForm.save() never touches it), but design.md was never updated to reflect the revision. WARNING, not CRITICAL - the spec requirement itself is satisfied and covered by 3 passing tests |
| D5, DefinicionDeTipoForm narrows fields, edit is borrador-only (404 otherwise) | Yes, exact match. forms.py: fields = ("archivo_yaml",); views.py::editar_definicion scopes its get_object_or_404 to estado=Estado.BORRADOR, confirmed by test_editar_definicion_no_borrador_404 |
| D6, activate/desactivate POST-only, PRG + messages | Yes, exact match. Both mutating views carry @require_POST; both redirect() back to tipos_detalle; message text matches admin.py's existing per-problem format "{ubicacion}: {mensaje}" |
| D7, deregistration removes only the two @admin.register(...) lines, classes/tests retained | Yes, exact match. admin.py confirmed: ModelAdmin/ModelForm classes present, undecorated; test_admin.py's 16 tests unmodified and passing; module docstring records the one-line-revert rationale |
| D8, no new upload validators, logo-keep needs no code | Yes, exact match. forms.py has no size/format validators on plantilla/archivo_yaml; test_crear_o_editar_plantilla_oversize_es_aceptada proves acceptance past Adjunto's ceiling; test_editar_tipo_sin_reupload_logo_mantiene_logo_existente proves the plain ModelForm default is sufficient |

One documented design deviation (D4's stale "disabled=True" text vs. the
shipped "exclude field" approach) - flagged as WARNING below, does not
break the spec.

## Correctness Issues Found (source inspection)

- D4 doc/code inconsistency (WARNING, primary finding of this pass):
  design.md's D4 section (lines ~119-130) still reads "Chosen:
  self.fields[\"plantilla\"].disabled = True" and its rationale table never
  mentions the exclusion approach. The actual shipped tipos_reporte/forms.py
  uses del self.fields["plantilla"] (confirmed via git show 084459c and
  direct file read) - a genuine, deliberate revision made during manual
  browser verification on 2026-08-30, correctly explained in forms.py's
  own module/class/inline docstrings and comments (all three internally
  consistent with each other and with the shipped behavior). design.md
  itself was never updated to match. This is documentation staleness, not
  a functional defect - no other file in the repository still describes
  disabled=True as the current mechanism (grepped "disabled" across all
  .py files: only 2 test files and forms.py's own comments reference it,
  all correctly describing it as the superseded approach). Recommend
  updating design.md's D4 table/prose before archive, for artifact
  hygiene and to avoid confusing a future reader who diffs design vs.
  code.
- tasks.md staleness (SUGGESTION): tasks 6.1 and 6.6's literal text
  (plantilla_disabled_true_..., .disabled = True when ...) was not
  updated to match the D4 revision, even though forms.py's comments and
  the actual test names were. Cosmetic only - the checked boxes correctly
  reflect completed, passing work.
- Root-cause analysis of the disabled=True bug is sound and confirmed by
  source inspection: a disabled=True FileField re-runs its
  bound_data/clean() path against the field's initial value on every
  form validation, and Django's FileField.clean() calls storage-existence/
  size-style checks against the file name. In DEBUG this project's default
  storage is FileSystemStorage, which attempts to resolve a Vercel Blob's
  full URL as a local filesystem path - exactly the failure mode the
  commit message describes. The exclusion fix (del self.fields["plantilla"])
  sidesteps this entirely because an excluded field is never touched by
  _clean_fields() or save(). This is a correct, minimal fix for the
  stated defect.
- No other FileField/ImageField in the codebase uses disabled=True under
  a condition where DEBUG's FileSystemStorage could diverge from
  production's VercelBlobStorage-persisted filename. Grepped "disabled"
  across every .py file in the repository: the only production-code hits
  are in tipos_reporte/forms.py's own comments (describing the rejected
  approach), plus two unrelated test-file hits
  (tipos_reporte/tests/test_formularios.py's test asserting
  form.fields["plantilla"].disabled is False, and an unrelated substring
  match in reportes/tests/test_views.py). admin.py's TipoDeReporteAdmin
  achieves its equivalent plantilla-readonly-once-active guard via
  ModelAdmin.get_readonly_fields (Django admin's own readonly-fields
  mechanism, which renders the field as plain text rather than a bound
  disabled form widget) - a structurally different, unaffected code path.
  No related risk found elsewhere in the codebase.
- No functional bugs found in tipos_reporte/views.py, urls.py, forms.py,
  validacion.py, admin.py, usuarios/decorators.py, or any of the four new
  templates.
- Navigation entry point to tipos_lista itself (a link in base.html's
  header) remains genuinely absent, consistent with design's still-open,
  unchecked Open Question ("Navigation entry point... Confirm the
  deferral."). This is distinct from the b5ebcd2 bugfix, which added
  links from lista.html/detalle.html to the create/edit routes - those
  two concerns do not contradict each other; both are confirmed correct
  by source inspection of base.html (no tipos-reporte/tipos_lista
  reference found) and lista.html/detalle.html (both link out to
  create/edit as the bugfix commit describes).
- design.md's two remaining unchecked Open Questions (navigation entry
  point; DefinicionDeTipo edit scope confirmation) are both documented
  deferrals with implemented, tested behavior behind them (borrador-only
  edit is implemented and tested via
  test_editar_definicion_no_borrador_404) - not silent gaps, but still
  open checkboxes. SUGGESTION: resolve/check them explicitly before or
  shortly after archive, same pattern flagged in prior verify reports for
  this project.
- proposal.md's Success Criteria checklist (4 items) remains all-unchecked
  despite the change being fully delivered with every criterion covered
  by a passing test. SUGGESTION: check them off before archive, same
  recurring hygiene item as prior verify reports (mis-reportes,
  sincronizacion-numero-registro).

## Assertion Quality

Scanned usuarios/tests/test_decorators.py,
tipos_reporte/tests/test_listado.py, test_vistas.py, test_formularios.py,
and the new regression test in test_generador.py. No tautologies, no
assertions that skip calling production code, no smoke-test-only patterns.
The 403 tests assert both the status code and the absence of leaked data
in the response body (e.g. assert tipo.codigo not in
response.content.decode()), a real behavioral pair rather than a single
weak assertion. The anonymous-redirect decorator test deliberately avoids
the database and asserts the view body never runs by using a dummy view
with distinguishable content (b"ok-vista-ejecutada"), not merely a status
code. The plantilla read-only tests assert the actual persisted value
after save() (guardado.plantilla.name == plantilla_original), not merely
that the form rendered a disabled/excluded widget.

Assertion quality: All assertions verify real behavior.

## Issues Summary

CRITICAL
None.

WARNING
1. design.md's D4 section documents the superseded disabled=True
   approach; the shipped forms.py correctly implements and documents the
   revised "exclude the field" approach. Recommend updating design.md's
   D4 table and prose before archive so the design artifact matches the
   code it describes. Does not block archive functionally (spec
   requirement is satisfied and tested) but is a real documentation
   inconsistency the user specifically asked to have checked.

SUGGESTION
1. tasks.md tasks 6.1/6.6's literal text still names the superseded
   disabled=True mechanism and an outdated test name; cosmetic only,
   consider updating for consistency with the actual shipped code.
2. design.md's two remaining unchecked Open Questions (navigation entry
   point deferral; DefinicionDeTipo edit-scope confirmation) have
   implemented, tested behavior behind them but remain open checkboxes -
   resolve/check explicitly before or shortly after archive.
3. proposal.md's Success Criteria checklist (4 items) is unchecked
   despite full delivery with passing coverage for each - check them off
   before archive for artifact hygiene (recurring pattern across this
   project's changes).

## Verdict

PASS WITH WARNINGS

All 15 requirements and all 23 scenarios of administracion-tipos-reporte
are implemented and proven by 369 passing tests (0 failed, 0 errors) run
directly against the real Neon Postgres test database in this
verification pass, independently reproducing and extending the
apply-progress claim (349 passed, scoped to 3 apps; 369 is the confirmed
full-repo total). All 77 tasks across 8 phases are checked, and each
checked task is backed by real, currently-passing code and tests - no
task was checked prematurely. 7 of 8 design decisions (D1, D2, D3, D5,
D6, D7, D8) are implemented exactly as designed with no deviations. D4
has one WARNING-level finding: the shipped code correctly and safely
implements a later, well-documented revision (field exclusion instead of
disabled=True, fixing a real DEBUG-vs-production storage crash), but
design.md itself was never updated to reflect that revision - a
documentation-artifact inconsistency, not a functional defect. No other
FileField/ImageField in the codebase carries the same
disabled=True-under-divergent-storage risk pattern. No CRITICAL issues
were found; the single WARNING and 3 SUGGESTION-level hygiene items do
not block archive but should be addressed (at minimum, the D4 WARNING)
for artifact accuracy.
