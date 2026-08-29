# Proposal: Wizard de captura server-rendered

## Intent

`DefinicionDeTipo` (backlog #3/#4) can declare a report's structure, but nothing yet lets a user actually capture data against it. Backlog #5 closes that gap: a server-rendered, multi-step wizard that reads `DefinicionDeTipo.estructura` and renders one HTML step per `seccion`, persisting captured values immediately. This is also the first definition of `Reporte`/`ValorDeReporte`, which #7 (visto bueno), #8 (colaboración), #9 (offline) and #10 (sync) all build on — getting the shape right now avoids costly rework later.

## Scope

### In Scope
- New `reportes/` app with `Reporte` (FK `TipoDeReporte`, FK `DefinicionDeTipo` snapshot, `creador`, `fecha_creacion`, minimal `estado`) and `ValorDeReporte` (FK `Reporte`, `identificador_de_campo`, `valor`, `autor`, `fecha`).
- One URL per `seccion`; one dynamically built Django `Form` per section from `campos`/`items`.
- Field-type → widget mapping: `texto`/text, `numero`/number, `fecha`/date, `hora`/time, `seleccion`/select, `booleano`/checkbox, `rango-hora-inicio-fin`/two time inputs writing `{id}_inicio`/`{id}_fin` rows.
- Per-step POST upserts `ValorDeReporte` durably (no session state).
- Back/forward navigation rehydrates forms from persisted rows.
- `obligatorio` → HTML `required` + visual marker only, no server blocking.
- No new dependency (no django-formtools), per ADR-0001.
- Strict TDD: tests first for models and views.

### Out of Scope
- Required-field enforcement, "No cumple" warnings (#6).
- Visto bueno / closing a report (#7).
- Invitations, collaboration, role-based access beyond creator-only (#8).
- Offline, service worker, IndexedDB (#9).
- Sync, `numero_registro` assignment (#10).

## Capabilities

### New Capabilities
- `reportes-modelo`: `Reporte`/`ValorDeReporte` models and their persistence contract (definition snapshot, one row per captured value, two rows for `rango-hora-inicio-fin`).
- `wizard-captura`: server-rendered multi-step capture flow — per-section URL/form, widget mapping, per-step persistence, back/forward rehydration.

### Modified Capabilities
None.

## Approach

Custom multi-step FBV-based view per section (no formtools). Each section's `Form` is built dynamically from `estructura["secciones"][i]["campos"/"items"]`. POST upserts `ValorDeReporte` rows keyed by `identificador_de_campo`; GET re-renders by reading existing rows back into initial form data. `Reporte` is created once (first step) and referenced by subsequent steps via URL param.

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `reportes/models.py` | New | `Reporte`, `ValorDeReporte` |
| `reportes/views.py` | New | Per-section wizard steps |
| `reportes/urls.py` | New | One path per `seccion` id |
| `reportes/templates/reportes/*.html` | New | Step form + nav shell |
| `config/settings.py` | Modified | Register `reportes` app |
| `config/urls.py` | Modified | `include()` reportes urls |
| `tipos_reporte/generador.py` | Modified | Extract public `claves_de_valor(nodo)` from `_destinos` so wizard and generator derive the same `ValorDeReporte.identificador_de_campo` key — prevents silent drift between what the wizard saves and what the generator reads |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Model shape wrong, costly for #7-#10 | Med | Keep minimal `estado`, snapshot FK to definition version, review before merge |
| No existing wizard/template convention | Low | Keep templates plain HTML5, project-level, matching ADR-0001 |
| Scope creep into validation/offline | Med | Explicit out-of-scope list enforced in spec/tasks |

## Rollback Plan

Revert the `reportes` app and its `INSTALLED_APPS`/`urls.py` registration; no other app depends on it yet, so rollback is a clean app removal plus migration reversal.

## Dependencies

- Backlog #3/#4 (`DefinicionDeTipo`, `estructura` schema, `TipoDeDato`) — already merged.

## Success Criteria

- [ ] User can complete all sections of a report's wizard and data persists per step.
- [ ] Navigating back/forward between steps preserves entered data.
- [ ] No per-`tipo` hardcoded view/template — rendering is fully data-driven from `estructura`.
- [ ] All models/views covered by tests written first (strict TDD).

## Proposal question round

All open decisions flagged in exploration were already confirmed by the user prior to this proposal (model shape, `rango-hora-inicio-fin` two-row contract, `booleano` as checkbox, per-step durable persistence, no new dependency, out-of-scope boundaries). No further product-shaping questions are outstanding; if any assumption above should change, flag before moving to `sdd-spec`/`sdd-design`.
