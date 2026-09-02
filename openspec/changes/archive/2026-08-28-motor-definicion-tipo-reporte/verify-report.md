# Verification Report: Report Type Definition Engine (backlog #3)

> Engram: `sdd/motor-definicion-tipo-reporte/verify-report`
> **THIS IS A RE-VERIFY** (second pass). Original verify below (unchanged,
> kept as historical record) found ONE CRITICAL. This section documents the
> fix and its independent re-confirmation; read this section first.

## RE-VERIFY (2026-08-28) - CRITICAL closed

**Inputs re-read**: spec revision 2 (Engram #73), tasks (Engram #75),
apply-progress (Engram #76, now revision 5 - documents the fix commit
`5391285`), and the original verify-report (Engram #77, preserved below).

**What changed since the original verify**: one additional commit,
`5391285` (`fix(tipos-reporte): allow DefinicionDeTipoForm to accept valid
uploads`), stacked on top of the same branch
`feat/motor-definicion-tipo-reporte-04-servicio-admin` (still the last of
the 4 stacked slices, no new branch). Only two files touched:
`tipos_reporte/admin.py` (`+20/-3`) and `tipos_reporte/tests/test_admin.py`
(`+51/-1`). Working tree is clean at this commit.

**Fix verified by reading the diff**: `DefinicionDeTipoForm.__init__` now
sets `self.fields["yaml_fuente"].required = False` and
`self.fields["estructura"].required = False`, moving the required-check out
of Django's `_clean_fields()` phase. `clean()` now raises
`ValidationError({"archivo_yaml": "Este campo es obligatorio."})` when
`archivo_yaml` is absent (previously it silently `return`ed, which combined
with the always-failing required fields, meant no form ever validated one
way or the other on this path). This is exactly the fix Finding A
prescribed (`required=False` + populate in `clean()`).

**Independent reproduction this session (not trusting the new tests
as-is)**: wrote a standalone scratch pytest file
(`tipos_reporte/tests/test_verify_reproduce_critical.py`, deleted after
use, never committed) with three cases NOT copy-pasted from
`test_admin.py`:

| Case | Result on current (fixed) code |
|---|---|
| Valid YAML upload (`secciones: []`) via `DefinicionDeTipoForm` | `is_valid() == True`; `cleaned_data["yaml_fuente"] == "secciones: []"`, `cleaned_data["estructura"] == {"secciones": []}` |
| Unsafe YAML (`!!python/object/apply:os.system [...]`) | `is_valid() == False`, `"archivo_yaml"` in `form.errors` |
| No file uploaded at all (`files={}`) | `is_valid() == False`, `"archivo_yaml"` in `form.errors` |

All three passed. Then, to prove this was a genuine test of the real
behaviour and not a vacuous pass, the pre-fix `admin.py`
(`git show c9d5328:tipos_reporte/admin.py`, the exact code the original
verify inspected) was swapped in temporarily and the same scratch suite
re-run: the valid-YAML case failed with the exact error the original
verify reported (`{'yaml_fuente': ['This field is required.'], 'estructura':
['This field is required.']}`), while the two rejection cases still passed
(expected - a form that rejects everything also "rejects" bad input, for
the wrong reason). This RED-on-old-code / GREEN-on-new-code round-trip
independently confirms the CRITICAL is genuinely closed, not closed by a
test that happens to pass regardless of the underlying code. The fixed
`admin.py` and the scratch test file were then restored/removed
(`git status` confirmed clean before and after).

**Also read `test_admin.py`'s own two new tests** (not just trusted by
existence): `test_form_es_valido_con_yaml_valido_subido` asserts
`form.is_valid()` plus both derived `cleaned_data` values, and
`test_form_sigue_rechazando_yaml_inseguro` asserts rejection with
`"archivo_yaml" in form.errors` for the unsafe-YAML case - both assert on
outcomes, not just "no exception raised", so they are genuine behavioural
tests, matching the independent reproduction above.

**Full suite re-run this session**: `.venv/Scripts/python.exe -m pytest -q`
→ `105 passed, 6 warnings in 80.26s`, exit 0 (103 from the original verify
+ 2 new: `test_form_es_valido_con_yaml_valido_subido`,
`test_form_sigue_rechazando_yaml_inseguro`). No regressions.

**Regression on the fix itself**: the two other genuine security/behaviour
tests the original verify confirmed (unsafe-YAML rejection,
`test_yaml_no_confiable_es_rechazado`; corrupt-.xlsx handling) are
untouched by this commit and still pass as part of the 105.

**WARNING re-check (untested logo-image validation, spec revision 2)**:
STILL OPEN, unchanged. `grep -rl "logo" tipos_reporte/ --include=*.py`
matches only `migrations/0001_initial.py`, `models.py`, and
`validacion.py` - no test file references `logo` at all. The fix commit
touched only `admin.py` and `test_admin.py`'s YAML-form tests; it does not
add or remove any logo coverage. This WARNING is carried forward
unmodified from the original verify (see Finding H below) - not addressed
in this re-verify pass, per the task's scope (confirm status, not fix it).

**Updated verdict**: **PASS, CRITICAL CLOSED.** The one blocking CRITICAL
from the original verify (Finding A) is fixed and independently
re-confirmed by an isolated, RED/GREEN-round-tripped reproduction, not
merely by the presence of new tests. No new CRITICAL was introduced by the
fix (2-file diff, narrowly scoped, full suite green, no other spec
requirement or design decision touched). One WARNING remains open (untested
logo-image validation) - informational, not blocking. **Nothing blocks
`sdd-archive`** unless the user wants the logo WARNING resolved first,
which is their call, not a hard gate (it was already classified WARNING,
not CRITICAL, in the original pass, and nothing changed that classification
here).

### Commands re-run this re-verify session

| Command | Result | Exit |
|---|---|---|
| `git log --oneline -5` / `git status` | `5391285` on top of `c9d5328`; working tree clean throughout | -- |
| `.venv/Scripts/python.exe -m pytest -q` | `105 passed, 6 warnings in 80.26s` | 0 |
| Scratch reproduction (3 independent cases, fixed code) | all pass, matching the fix's intended behaviour | -- |
| Scratch reproduction (same 3 cases, pre-fix `admin.py` swapped in) | valid-YAML case fails with the exact original CRITICAL error; both rejection cases still pass | -- |
| `grep -rl "logo" tipos_reporte/ --include=*.py` | only `migrations/`, `models.py`, `validacion.py` - no test file | -- |

---

## Original verify (Engram #77, preserved below, unchanged)

# Verification Report: Report Type Definition Engine (backlog #3)

> Engram: `sdd/motor-definicion-tipo-reporte/verify-report`
> Inputs: spec revision 2 (Engram #73), design (Engram #74), tasks
> (Engram #75), apply-progress (Engram #76, covers all 4 stacked slices).
> This verify runs over the COMPLETE change (all 4 slices together, working
> tree at commit `c9d5328` on branch
> `feat/motor-definicion-tipo-reporte-04-servicio-admin`, stacked on
> `main` through the 3 prior slice branches), not per-slice.

## Scope

All 10 spec requirements / 20+ scenarios of spec revision 2 (Engram #73),
all 10 design decisions (Engram #74), and the full 4-slice apply-progress
(Engram #76), including the one bugfix discovered during Slice 4.

## Verdict

**PASS WITH ONE CRITICAL** - do not archive until the CRITICAL below (the
admin's own DefinicionDeTipo save form is non-functional as coded) is
either fixed or explicitly accepted with a documented exception.

- Automated suite: PASS. 103/103 tests green, re-run independently this
  session (not merely re-stated from apply-progress). `manage.py check`
  clean.
- Model/versioning/immutability/delete-guard decisions (D1-D3, D9): PASS,
  re-derived directly against the code, including a mutation-testing
  re-confirmation of the Slice-4 bugfix.
- Security threat matrix (YAML deserialization, corrupt .xlsx): PASS, the
  two REDs are genuine behavioural tests, not name-absence.
- **CRITICAL**: `DefinicionDeTipoForm` (the actual "administrator uploads a
  YAML file through the stock admin" path required by two spec
  requirements) is never exercised by any of the 103 tests, and when
  independently probed this session, it is provably broken - it rejects
  every submission, including a fully valid one, because `yaml_fuente` and
  `estructura` are required model fields that the admin's own HTML form
  never supplies data for before `clean()` runs. See Finding A.
- Line-budget overrun (~2124 actual vs ~1082-1210 forecast, ~90-96% over)
  is an already-accepted exception from apply, restated below per this
  skill's convention (mirrors despliegue-e-infraestructura's Engram #56
  precedent) - not reopened as a new finding.

## Commands re-run this session (real output, real exit codes)

| Command | Result | Exit |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | `103 passed, 6 warnings in 73.43s` | 0 |
| `.venv/Scripts/python.exe -m pytest -q` (re-run after mutation testing, to confirm baseline restored) | `103 passed, 6 warnings in 72.58s` | 0 |
| `.venv/Scripts/python.exe manage.py check` | `System check identified no issues (0 silenced).` | 0 |
| `.venv/Scripts/python.exe -m pytest usuarios -q` | `17 passed, 6 warnings in 30.90s` | 0 |
| `.venv/Scripts/python.exe -m pytest --collect-only -q` | `103 tests collected` (18 config + 68 tipos_reporte + 17 usuarios) | 0 |
| `git status` / `git log --oneline -8` | working tree clean; all 4 slice commits present in order on top of the deployment commits | -- |

Test-count arithmetic independently verified: 68 tipos_reporte tests total
this change (51 from Slices 1-3 + 17 new in Slice 4) + 17 usuarios (item
#1, untouched) + 18 config (item #2 deployment, untouched) = 103. Matches
apply-progress's own "86 prior + 17 new" claim (86 = 18 + 17 + 51).

## A. CRITICAL - `DefinicionDeTipoForm` never actually accepts a valid submission, and no test exercises it

**What was checked.** grep across `tipos_reporte/tests/` for any reference
to `DefinicionDeTipoForm` (the class implementing design D4's "administrator
uploads a YAML file, it is parsed and validated at save time" gate).
Zero matches. All three test files that touch `DefinicionDeTipo`
(`test_modelos.py`, `test_activacion.py`, `test_admin.py`) construct rows
directly via `DefinicionDeTipo.objects.create(...)`, bypassing the
ModelForm/admin save path entirely. `test_admin.py`'s activation tests
exercise `admin.activar()` (the service call) on an already-`.create()`-d
row, which is a different code path from actually saving a new
`DefinicionDeTipo` through the admin's add/change form.

**Independent reproduction this session.** Built `DefinicionDeTipoForm`
directly with a valid `TipoDeReporte`, `estado="borrador"`, and a real
`archivo_yaml` upload (`secciones: []`, valid YAML) - the exact shape an
administrator would submit through `/admin/tipos_reporte/definiciondetipo/add/`:

```
form = DefinicionDeTipoForm(data={"tipo": tipo.pk, "estado": "borrador"}, files=files)
form.is_valid()  ->  False
form.errors  ->  yaml_fuente: This field is required.
                 estructura: This field is required.
```

**Root cause.** `DefinicionDeTipoForm.Meta.fields = "__all__"` includes
`yaml_fuente` (TextField, not `blank=True`) and `estructura` (JSONField, not
`blank=True`) as ordinary form fields. Django's `full_clean()` runs
`_clean_fields()` (which enforces each field's own `required=True`,
because `blank=False` on the model) BEFORE `clean()` runs. `clean()` is
where `DefinicionDeTipoForm` populates `cleaned_data["yaml_fuente"]` and
`cleaned_data["estructura"]` from the parsed `archivo_yaml` - but by the
time `clean()` runs, `_clean_fields()` has already recorded "This field is
required" errors for both, because the admin's rendered form never asks an
administrator to type YAML text or a JSON tree by hand (that is the entire
point of parsing from `archivo_yaml`). The form is therefore invalid for
every submission, valid or malformed, and no `DefinicionDeTipo` can ever be
saved through the stock Django admin as currently wired.

**Which spec requirements this breaks.** Directly falsifies:
- "DefinicionDeTipo model and YAML loading" -> scenario "Valid YAML upload
  is parsed and normalized" (an administrator can never successfully save
  one through the admin).
- "Django admin integration for definition and activation" -> scenario
  "Administrator activates a type from the stock admin" (there is no way
  to reach a savable, activatable `DefinicionDeTipo` through the admin
  UI at all - the precondition of that scenario is unreachable).

The "Malformed YAML is rejected at save time" scenario happens to still
pass its outcome (`is_valid() == False`) for the wrong reason and for
every input, not specifically for malformed YAML - it is not evidence the
scenario is actually satisfied, only that a broken form and a correctly
rejecting form are indistinguishable by that scenario's own assertion
shape ("save MUST be rejected"). This is exactly the kind of thing a
test that submits through the real form (not `.objects.create()`) would
have caught, and none of the 103 tests do.

**Why this was not caught by Strict TDD as practiced.** Every RED in this
slice was driven by "does the service/admin action exist and behave
correctly", never by "does an administrator's actual browser submission
succeed". The two admin tests that construct a `DefinicionDeTipo` and then
call `admin.activar()` are genuine RED/GREEN for the *activation* action
(and mutation-tested as such, see Finding B below) - they simply never
touch the *save* path this bug lives in.

**Classification: CRITICAL.** This is not a design deviation (the design's
own D4 prose is correct - split the concerns) and not a spec gap (the spec
text is correct too) - it is an implementation bug with zero test coverage,
directly blocking the one end-to-end workflow ("an administrator uploads a
YAML file and it gets used") every other spec requirement in this change
depends on. Must be fixed (e.g. exclude `yaml_fuente`/`estructura` from the
ModelForm's required-field set with `required=False` plus populating them
in `clean()`/`save()`, or move both into `exclude` and set them directly on
the instance in `ModelForm.save(commit=False)`) and covered by at least one
test that submits through `DefinicionDeTipoForm` (or the admin test client)
before this change can be honestly archived as satisfying the spec it
claims to satisfy.

## B. RED genuineness re-derived via mutation testing (not accepted from design/tasks as-is)

Per the requested rigor, three of the design own genuine and
behavioural claims were independently re-derived this session by
temporarily reverting the production code to a plausible broken
implementation, confirming the test suite actually fails, then reverting
(git checkout --) and re-confirming 103/103 green.

| Claim re-derived | Mutation applied | Result |
|---|---|---|
| R6 (merge-anchor rule) is a genuine behavioural RED | Neutered the per-cell anchor check in validar_contra_plantilla to "if False" (never reports celda-no-es-ancla) | 2 tests failed: test_celda_no_ancla_de_rango_combinado_es_rechazada and test_composer_acumula_problemas_estructurales_y_de_plantilla. Confirmed genuine. |
| Settled decision 4 (accumulate all errors, never stop at first) is the sole mechanical proof the design claims | Made validar_estructura per-node loop return early as soon as any problem exists (stop-at-first-error) | 2 tests failed: test_todos_los_problemas_acumulados_se_reportan_en_un_solo_intento and test_acumulacion_no_se_detiene_en_el_primer_error. Confirmed genuine. |
| The Slice-4 immutability-guard bugfix (design D3, anterior.estado vs self.estado) is real and its regression test actually catches it | Reverted models.py save() guard from anterior.estado check back to the original buggy self.estado check | 6 tests failed across 2 files: the dedicated regression test in test_modelos.py PLUS all 5 non-trivial tests in test_activacion.py. Confirms the bug was not a narrow edge case and the fix is correctly gated on the row PREVIOUS state, not its new one. No hole found in the fix. |

All three mutations were reverted with git checkout -- immediately after
observing the failure; git status confirmed a clean tree and the full
suite was re-run green (103/103) before continuing. This sample is
representative of the design strongest claims and its one real defect
found during apply; all three held up under adversarial mutation. The
three claims flagged by the design itself as weak name-absence RED
(catalogue membership, admin readonly_fields, MEDIA_ROOT set) were not
re-derived, matching the design own honest classification of them as
non-behavioural.

## C. Design decisions verified against real code

| Decision | Verified | Evidence |
|---|---|---|
| D1 - FK definicion_activa, not a mirrored boolean | PASS | TipoDeReporte.activo is a @property over definicion_activa_id is not None (models.py:125-127); definicion_activa is ForeignKey(..., on_delete=models.PROTECT) (models.py:105-111). No boolean field exists on TipoDeReporte. |
| D2 - version assigned once, never reassigned | PASS | servicios.activar_definicion only sets definicion.version = _siguiente_version(tipo) inside "if definicion.version is None" (servicios.py:59-60) - a re-activation of a historica row (version already set) skips this branch entirely and keeps its original version. test_reactivar_definicion_historica_reusa_su_version_original exercises this directly. |
| D3 - immutability via save() + QuerySet.update() guard, no DB trigger | PASS (as an honestly-limited guarantee) | CONGELADOS fields checked against anterior (freshly fetched), gated on anterior.estado != BORRADOR (models.py:205-225, the Slice-4 fix, re-confirmed genuine in Finding B). DefinicionDeTipoQuerySet.update() independently raises for the same fields on non-draft rows (models.py:52-62), proven by test_queryset_update_bypassing_immutability_on_activa_row_raises. No BEFORE UPDATE trigger exists - matches the design own stated residual gap; not a new finding. |
| D4 - parse/validate frontier (save vs activation) | PARTIALLY BROKEN | The activation-time validator (validar_definicion, R1-R6) correctly runs only at activation, never at save - confirmed. The save-time gate (DefinicionDeTipoForm.clean(), meant to reject documents that cannot become JSON) is unreachable for a normal, valid submission at all - see Finding A (CRITICAL). The frontier design is correct; its implementation of the save-time half is broken. |
| D5 - two pure functions + composer, regla as stable identifier | PASS | validar_estructura/validar_contra_plantilla take no DB/model arguments; every test asserts on sets of p.regla, never on mensaje text. |
| D6 - hoja required key | PASS | validar_contra_plantilla returns hoja-ausente when estructura.get("hoja") is falsy, and hoja-no-encontrada when the named sheet is absent from libro.sheetnames (validacion.py:243-265), exactly matching spec revision 2 two new scenarios. Both are behaviourally tested. |
| D7 - version_formato vs DefinicionDeTipo.version | PASS | TipoDeReporte.version_formato is a separate CharField (models.py:100); DefinicionDeTipo.version is the PositiveIntegerField (models.py:159). No naming collision. |
| D8 - activation is an explicit admin action calling a service, never a save() hook | PASS | activar_definicion lives in servicios.py, called only from DefinicionDeTipoAdmin.activar (an @admin.action), never from DefinicionDeTipo.save(). Validation runs outside any transaction; only a clean result enters transaction.atomic() (servicios.py:34-69). |
| D9 - deletion blocked at model layer + admin, with the has_delete_permission(obj=None) nuance | PASS | Layered exactly as designed: DefinicionDeTipo.delete() and .QuerySet.delete() both raise for any ever-activated row (models.py:64-70, 227-233); TipoDeReporte mirrors this (models.py:73-83, 129-135); the FK uses on_delete=PROTECT. Admin: get_actions() pops delete_selected entirely for BOTH admins (admin.py:86-89, 121-124) rather than relying on the object-level check; has_delete_permission(request, obj=None) correctly falls through to super() when obj is None (admin.py:91-94, 126-131), matching the documented Django gotcha. Both the bulk-action removal and the object-level check at both permission states are directly tested. |
| D10 - MEDIA_ROOT/MEDIA_URL/Pillow prerequisite | PASS | config/settings.py sets MEDIA_URL and MEDIA_ROOT (new, confirmed absent before this item); Pillow in requirements.txt; /media/ added to .gitignore. manage.py check clean. |

The four load-bearing decisions the task specifically asked about: D1 and
D2 are solid and directly evidenced by both static code reading and the
mutation-testing re-derivation in Finding B. D4 is where the divergence
lives - the decision (where the frontier sits) is correctly designed and
correctly implemented for the activation half, but the save-time half
concrete Django wiring does not actually let a real submission reach the
frontier at all (Finding A). D9 verified clean, including the specific
has_delete_permission(obj=None) nuance the task called out by name.

## D. Security threat matrix verified (both applicable boundaries)

| Boundary | Test | Verified real, not name-only |
|---|---|---|
| Untrusted deserialization (uploaded YAML) | test_yaml_no_confiable_es_rechazado feeds a literal "!!python/object/apply:os.system" tag into analizar_yaml_seguro and asserts yaml.YAMLError is raised | PASS. Read the implementation: analizar_yaml_seguro is a one-line wrapper around yaml.safe_load, never yaml.load. SafeLoader has no constructor registered for that tag by construction (a PyYAML library guarantee, not project code), so the test is a real behavioural proof, not a mock. Positive counterpart test_yaml_seguro_es_analizado_normalmente confirms ordinary YAML still parses. |
| Untrusted file parsing (uploaded .xlsx) | test_plantilla_ilegible_produce_un_unico_problema feeds a BytesIO of plain non-xlsx bytes into validar_contra_plantilla and asserts exactly one plantilla-ilegible problem, no exception propagates | PASS. Read the implementation: validar_contra_plantilla wraps load_workbook(plantilla) in a bare except Exception, returning exactly one problem and short-circuiting the rest of that function (R1-R4 problems from validar_estructura still separately reported by the composer, confirmed by test_composer_reporta_r1_r4_junto_a_plantilla_ilegible). No 500, no partial per-cell checks against a workbook that never opened. |

Both threat-matrix REDs are genuine, targeted, behavioural tests, not
merely present by name.

## E. Spec compliance matrix (spec revision 2, Engram #73)

| Requirement | Status | Note |
|---|---|---|
| TipoDeReporte model (inactive by default, codigo uniqueness) | PASS | test_tipo_de_reporte_is_created_inactive_by_default, test_codigo_uniqueness_is_enforced |
| DefinicionDeTipo model and YAML loading (valid parse, malformed reject) | **CRITICAL gap** | See Finding A - the save path this requirement describes does not work through the real admin form; no test exercises the real form either |
| Definition names its sheet (hoja required, sheet must exist) | PASS | validacion.py hoja-ausente / hoja-no-encontrada rules, both behaviourally tested |
| Versioning - edit requires deactivation first | PASS (at the model/service layer) | Immutability enforced by save() guard (re-confirmed via mutation testing); deactivate-then-edit-then-reactivate flow proven by test_reactivar_definicion_historica_reusa_su_version_original. Note: because of Finding A, an administrator cannot reach this flow through the stock admin form today, only through direct ORM/service calls (which is how every test reaches it) |
| Closed data-type catalog (7 types, reject unknown) | PASS | TipoDeDato enum + _validar_tipo_conocido; tested positive and negative |
| Exhaustive activation validation (accumulate all errors, R1-R6) | PASS | Re-derived via mutation testing (Finding B), not merely accepted from the design/tasks narrative |
| Deletion blocked after any successful activation | PASS | Layered model + queryset + admin guards, all independently tested (see D9 above) |
| Django admin integration for definition and activation | **CRITICAL gap** | The "activate" half works (D8, tested); the "administrator uploads a template, uploads a YAML definition" half does not (Finding A) - the scenario as spec-written is not reachable end to end |
| Extending with a second report type requires no code change | PASS | test_segundo_tipo_estructuralmente_distinto_se_activa_sin_cambios activates a second, structurally distinct definition against a second template using the same unmodified validar_definicion/servicios code |
| Local file storage for uploads (template retrievable) | PASS, indirectly | Not tested as a named scenario, but exercised as a necessary side effect: test_activacion.py and test_admin.py save a real .xlsx to a TipoDeReporte.plantilla FileField, then activar_definicion opens and re-reads it via openpyxl inside the same test - this only works if MEDIA_ROOT/FileSystemStorage genuinely round-trip the file |
| Local file storage for uploads (logo image validated, non-image rejected) | **WARNING - untested** | No test in the suite ever sets TipoDeReporte.logo, valid or invalid. Whether a non-image file uploaded as logo is actually rejected (which depends on Django ImageField validation running through full_clean()/a ModelForm, not a bare .objects.create()) is unverified by this test suite. Likely works via Django/Pillow defaults given TipoDeReporteAdmin uses a stock ModelForm with no exclusion of logo, but "likely" is not "proven" - flagged as WARNING, not CRITICAL, because it is lower-stakes than Finding A (an optional field, not the core workflow) and Pillow presence was independently confirmed via manage.py check passing |

## F. Line-budget overrun (accepted exception, restated per convention)

| Slice | Forecast | Actual | Overrun |
|---|---|---|---|
| 1 (models) | ~330 | 537 | +63% |
| 2 (structural validation R1-R4) | ~290 | 503 | +73% |
| 3 (template validation R5-R6 + security) | ~200 | 421 | +111% |
| 4 (activation service + admin) | ~262-390 | 663 | +70-150% |
| Total | ~1082-1210 | ~2124 | ~+90-96% |

This is not a new finding. The design own Review Workload Forecast flagged
400-line-budget risk as High before apply started, and the user explicitly
resolved it by choosing a 4-slice stacked-to-main chain (delivery_strategy
ask-on-risk, decision already made and recorded in apply-progress, Engram
#76). Restated here, in the same size:exception spirit as the archived
despliegue-e-infraestructura change (Engram #56), for a complete verify
record - not reopened or treated as blocking.

## G. usuarios and config (items #1/#2) regression check

Both apps unaffected: usuarios/tests (17/17) and config/tests (18/18, part
of the 103 total, deployment settings from item #2) pass unchanged. No file
under usuarios/ or config/ was touched by this change except the additive
INSTALLED_APPS entry, MEDIA_ROOT/MEDIA_URL, and requirements.txt in
config/settings.py and requirements.txt - all confirmed by reading the
settings diff context and by usuarios re-run in isolation this session.

## H. Findings

### CRITICAL

1. DefinicionDeTipoForm rejects every submission, including a fully valid
   one, because yaml_fuente and estructura are required ModelForm fields
   with no data supplied by the admin real HTML form before clean() runs
   (Finding A). No test in the 103-test suite exercises this form. This
   breaks the "Valid YAML upload is parsed and normalized" and
   "Administrator activates a type from the stock admin" spec scenarios
   at the root - there is currently no way for an administrator to reach a
   savable DefinicionDeTipo through the stock Django admin at all. Must be
   fixed (exclude yaml_fuente/estructura from required ModelForm validation
   and populate them in clean()/save() instead) plus covered by a test that
   submits through the real form, before this change is archived as
   satisfying the spec it claims to satisfy.

### WARNING

1. The "An uploaded logo image is validated and persisted... non-image
   file rejected" spec scenario (revision 2 addition) has zero test
   coverage. Behavior is plausible (stock Django ImageField + Pillow,
   both confirmed present and manage.py check clean) but unverified.
   Lower severity than Finding A because logo is optional and not on the
   critical activation path.
2. Two of the design 13 recorded deviations remain informational only,
   not re-litigated here: analizar_yaml_seguro wiring collapsed into one
   ModelForm.clean() rather than split ModelForm.clean() +
   DefinicionDeTipo.clean() (functionally harmless, already the actual
   root of Finding A is unrelated to this specific split); and
   TipoDeReporteAdmin got its own undocumented desactivar action (harmless
   addition, exercised by test_admin.py indirectly through
   servicios.desactivar_tipo's own direct tests).
3. Line-budget overrun (~90-96% over the design own forecast, Finding F) -
   already an accepted, user-resolved exception; restated for the archive
   record only.

### SUGGESTION

1. Once Finding A is fixed, add at least one admin-integration test that
   goes through Django test client POST to
   /admin/tipos_reporte/definiciondetipo/add/ (not just the ModelForm in
   isolation), so a future regression in URL wiring, permissions, or
   admin-site registration is also caught, not only form-level logic.
2. Consider a small script or CI check to keep the two DefinicionDeTipo/
   TipoDeReporte delete-guard layers (model + queryset + admin) from
   silently drifting apart as new admin actions are added - the current
   coverage is thorough but entirely manual/enumerated.

## I. TDD / regression status

103/103 tests green, independently re-run twice this session (before and
after mutation testing), plus usuarios (17/17) and the full collection
count (103) cross-checked arithmetically against apply-progress own
breakdown. The design own RED classification (roughly 30 genuine
behavioural REDs, 3 weak name-absence REDs, D3 own admitted no-DB-backstop
limit) was not accepted at face value - three of its strongest claims
(R6 anchor rule, the accumulation composer, and the one real Slice-4
bugfix) were independently re-derived via mutation testing this session
(Finding B) and all three held up.

## Next steps

1. Before archive: fix Finding A (CRITICAL) - DefinicionDeTipoForm must
   actually accept a valid admin submission - and add at least one test
   that proves it, or have the user explicitly accept the current gap as
   a documented, permanent exception (matching the pattern used for the
   line-budget overrun) with a clear note that the admin YAML-upload path
   does not work yet.
2. Resolve the WARNING about untested logo-image validation before or
   shortly after archive - either add the missing test or explicitly
   accept the gap.
3. Once (1) is resolved, this change is otherwise ready for sdd-archive -
   every design decision, every other spec requirement, the full test
   suite, and both prior items (#1, #2) are confirmed intact.

Related: [[sdd/motor-definicion-tipo-reporte/apply-progress]],
[[sdd/motor-definicion-tipo-reporte/tasks]],
[[sdd/motor-definicion-tipo-reporte/design]],
[[sdd/motor-definicion-tipo-reporte/spec]].
