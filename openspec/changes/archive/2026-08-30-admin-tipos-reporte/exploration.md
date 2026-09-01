# Exploration: Administración de tipos de reporte (S-14, backlog #13)

## Current State

`TipoDeReporte`/`DefinicionDeTipo` CRUD exists **only** via Django admin (`tipos_reporte/admin.py`, backlog #3 archived) — no dedicated screen, views, templates, or URLs exist for it yet. Key baseline the new screen must match: `DefinicionDeTipoAdmin` parses uploaded YAML at save time (`analizar_yaml_seguro` = `yaml.safe_load` only) and offers an explicit "Activar definición" bulk action calling `tipos_reporte/servicios.py::activar_definicion` (validates fully before any DB write, atomic transition, never reassigns `version` on re-activation). `TipoDeReporteAdmin` locks `plantilla` readonly once a definition is active and offers "Desactivar tipo de reporte" (`servicios.py::desactivar_tipo`). Both models block hard-delete once ever-activated (model + QuerySet level).

**Logo "fallback" resolved from two independent sources** — not ambiguous:
1. Form-level (TECH-DESIGN.md checklist): editing a `TipoDeReporte` without re-uploading a logo must *keep* the existing one — Django's default `ModelForm`/`ClearableFileInput` gives this for free if reused.
2. Generation-time (already implemented, `generador.py::_intercambiar_logo`): if `TipoDeReporte.logo` is empty, the `.xlsx` template's own embedded logo is left untouched rather than blanked. This is done; S-14 only needs to not break it.

**"Checklist propio, ej. PPI Shotcrete"**: `adrs/0003-modelo-de-datos-y-plantillas.md` confirms a second real report format (PPI Shotcrete) exists as hidden sheets in the reference workbook and motivated the declarative `DefinicionDeTipo` design — but **no sample YAML/plantilla for it exists anywhere in the repo**. This is a forward-looking manual acceptance scenario (does "new type = configuration only" really hold?), not a blocker.

**Reusable precedents**: `reportes/listado.py` + `reportes/views.py::mis_reportes` (backlog #12, archived) is the established list/search/pagination pattern (pure query helpers + `Paginator.get_page` + GET-param filters). `reportes/adjuntos.py::validar_adjunto` (backlog #11, archived) is the established format-allowlist + size-ceiling upload-validation pattern — but note `logo`/`plantilla`/`archivo_yaml` have **zero** existing format/size validators today, so this is new validation surface, following the pattern not the code. `usuarios/models.py::Usuario.rol`/`es_administrador` exists as the role source of truth, but no `user_passes_test`-style decorator precedent exists yet outside plain `@login_required`.

## Affected Areas

- `tipos_reporte/views.py`, `urls.py`, `templates/tipos_reporte/` — all net-new (no dedicated screen exists).
- `tipos_reporte/forms.py` (new) — logo/plantilla/archivo_yaml upload forms; candidate to extract `DefinicionDeTipoForm`'s YAML `clean()` from `admin.py` into a shared parser.
- `tipos_reporte/servicios.py`, `validacion.py` — already UI-agnostic, reusable unchanged.
- `reportes/listado.py`, `reportes/views.py::mis_reportes` — pattern reference for the new list view.
- `reportes/adjuntos.py` — pattern reference (not code reuse) for new validators.
- `usuarios/models.py::Usuario.es_administrador` — access-control gate, new decorator needed.
- `config/storage.py` — reused as-is.

## Approaches

1. **Full custom S-14 screen** (list + create/edit + activate/desactivate), admin left untouched as fallback.
   - Pros: full UX control, in-scope per BACKLOG framing.
   - Cons: largest surface, duplicates YAML-parsing unless extracted.
   - Effort: High.

2. **Thin screen wrapping existing services** (`servicios.py`/`validacion.py` already do all business logic).
   - Pros: smallest slice given logic reuse.
   - Cons: still needs new forms/templates/access-control (most of S-14's actual work).
   - Effort: Medium.

3. **Improve Django admin UX instead of a separate screen**.
   - Pros: near-zero new surface.
   - Cons: contradicts BACKLOG's explicit "dedicated user-facing screen" framing.
   - Effort: Low but likely rejected.

4. **Split into two slices**: read (list/detail/activate/desactivate) first, upload-forms-with-validation second.
   - Pros: unblocks visibility fast, isolates the riskier new validation work.
   - Cons: admin still needed for creation until slice 2.
   - Effort: Medium (split).

## Recommendation

Approach 2, sliced per Approach 4 if `sdd-tasks`' 400-line review-budget forecast flags risk. `servicios.py`/`validacion.py` need zero changes; net-new work is list/detail views (listado.py pattern), upload forms with format+size validators (adjuntos.py pattern), and a new admin-role decorator — while preserving both already-resolved logo-fallback behaviors.

## Open Decisions (must be settled in proposal)

1. Does S-14 fully replace Django admin access to `tipos_reporte`, or coexist alongside it?
2. Single-slice vs. split delivery (review-budget impact).
3. Extract the YAML-parsing `clean()` logic from `admin.py` into a shared helper, now or later?
4. Format/size ceilings for `logo`/`plantilla`/`archivo_yaml` are undefined anywhere — must be decided.
5. Is a PPI Shotcrete second-type configuration exercise in scope for this change, or a separate future backlog item?

## Risks

- Duplicating untrusted-YAML-deserialization logic between admin.py and a new form is a security footgun if not extracted.
- No format/size validator precedent exists for these three fields — new validation surface, three different content types.
- `VercelBlobStorage.exists()` always `False` — re-uploads orphan old blobs, no cleanup mechanism.
- S-14 UI must replicate admin's `plantilla`-readonly-once-active guard or risk breaking active definitions' cell mappings.
- No admin-role access-control decorator precedent exists yet in the codebase.
- PPI Shotcrete has zero sample data — its business rules, if used as acceptance scenario, must be sourced from the original reference Excel.

## Key Learnings

1. Backlog #13's "logo con fallback" resolves to two independent, already-partially-solved behaviors: form-level "keep existing on no re-upload" and generation-time "template default if none set" (the latter already implemented in `generador.py`).
2. `tipos_reporte/servicios.py` and `validacion.py` are fully UI-agnostic and require zero changes for a new admin screen — all business logic already lives outside `admin.py`.
3. `logo`/`plantilla`/`archivo_yaml` have no existing format/size validators anywhere, unlike `Adjunto` uploads which already established that pattern in backlog #11.
4. PPI Shotcrete (the "checklist propio" context) is a real second report format referenced in ADR-0003 but has zero sample YAML/plantilla data in the repo today.
5. No admin-role access-control decorator precedent exists in this codebase yet — `Usuario.es_administrador` exists but nothing gates a view on it outside Django admin's own `is_staff` check.

**Next**: sdd-propose (pending the 5 open decisions above)
