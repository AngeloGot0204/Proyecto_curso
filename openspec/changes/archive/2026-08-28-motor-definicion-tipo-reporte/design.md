# Design: Report Type Definition Engine (backlog #3)

> Engram: `sdd/motor-definicion-tipo-reporte/design` (observation #74)
> Full verbatim text (all rationale tables, code excerpts, Data Flow diagram,
> Testing Strategy RED classification table, Threat Matrix, and Review
> Workload Forecast) lives in Engram observation #74 and is the authoritative
> copy. This file is a condensed index for filesystem archival, mirroring the
> pattern used by docs/sdd/archive/2026-08-27-despliegue-e-infraestructura/04-design.md.

## Technical Approach

New app `tipos_reporte`: two models, one pure validation module, one thin
activation service, a stock ModelAdmin pair. Three-layer separation:
YAML bytes --parse--> estructura (JSONField) --validate--> activation (DB write).

## Architecture Decisions (10)

- D1: `DefinicionDeTipo` is a version row; `TipoDeReporte.activo` is a
  foreign key (`definicion_activa`), not a mirrored boolean.
- D2: `version` is assigned once, at the draft's first successful activation,
  and never reassigned. Re-activating a historica row reuses its version.
- D3: Immutability enforced in `save()` (CONGELADOS fields) plus a
  `QuerySet.update()` guard; explicitly NOT database-backed (no BEFORE UPDATE
  trigger) - a stated, accepted residual gap for raw SQL.
- D4: The parse/validate frontier is "can this become a JSON document?" (at
  save, via yaml.safe_load) vs. "is this a valid definition?" (at
  activation, via the full R1-R6 validator).
- D5: The validator is two pure functions (`validar_estructura`,
  `validar_contra_plantilla`) plus a composer (`validar_definicion`) that
  never returns early - accumulation is structural (concatenation), not a
  convention.
- D6: The definition must name its sheet - `hoja` is a required key
  ([needs-spec], absorbed into spec revision 2).
- D7: `TipoDeReporte.version_formato` (client's document revision string,
  e.g. "F1") and `DefinicionDeTipo.version` (system-assigned content-snapshot
  integer) are different fields, deliberately named differently.
- D8: Activation is an explicit admin action calling `servicios.activar_definicion`,
  never a `save()` hook. Nothing is mutated until `resultado.es_valida` is True;
  the state transition itself runs inside `transaction.atomic()`.
- D9: Deletion is blocked at the model layer (`save()`/`delete()`/QuerySet
  overrides) plus PROTECT on the FK; the admin layer is "only the polite
  half" because Django calls `has_delete_permission(request, obj=None)`
  (no object) for the bulk `delete_selected` action, so `delete_selected`
  is removed from `actions` entirely rather than trusted to the
  object-level check ([needs-spec], absorbed into spec revision 2).
- D10: `MEDIA_ROOT`/`MEDIA_URL` must be added (none existed before this
  item); Pillow is required by ImageField; Vercel's read-only filesystem
  means uploads will not work on the deployed site until item #11
  ([needs-spec], absorbed into spec revision 2).

## File Changes (planned)

tipos_reporte/{__init__,apps,models,validacion,servicios,admin}.py,
migrations/0001_initial.py, tests/{conftest,test_validacion_estructura,
test_validacion_plantilla,test_modelos,test_activacion,test_admin}.py;
config/settings.py (INSTALLED_APPS, MEDIA_ROOT, MEDIA_URL); requirements.txt
(PyYAML, openpyxl, Pillow); .gitignore (/media/).

## Testing Strategy / Strict TDD RED classification (design's own claim)

Roughly 30 of the planned tests are genuine behavioural REDs (R1-R6 rules,
the accumulation test, R6 anchor positive/negative, immutability +
QuerySet.update() guard, the 4 DB constraints, delete guards, clean failure
on activation). 3 are weak name-absence REDs (catalogue membership, admin
readonly_fields, MEDIA_ROOT set). D3's immutability invariant is explicitly
recorded as having no database backstop.

## Threat Matrix (2 applicable boundaries)

- Untrusted deserialization (uploaded YAML): yaml.safe_load only; a
  `!!python/object/apply` tag must be rejected, not executed.
- Untrusted file parsing (uploaded .xlsx): load_workbook wrapped, any
  exception becomes exactly one `plantilla-ilegible` problem, never a 500.

## Review Workload Forecast (design's own estimate)

~1082 authored lines (2.7x the 400-line budget). Chained-PR split
recommended: Slice 1 (~330, models), Slice 2 (~290, R1-R4), Slice 3 (~200,
R5-R6 + security), Slice 4 (~262, service + admin). See 07-verify.md for
the actual authored totals and overrun analysis.

## Open Questions (all resolved before/during apply)
- [needs-spec] hoja required key (D6) -> absorbed into spec revision 2.
- [needs-spec] MEDIA_ROOT/Pillow (D10) -> absorbed into spec revision 2.
- Deployed-site upload limitation (D10) -> accepted, deferred to item #11.
- D3's no-database-backstop -> accepted, deferred as a follow-up.
- Chained-PR split -> user explicitly chose stacked-to-main (see apply-progress).
