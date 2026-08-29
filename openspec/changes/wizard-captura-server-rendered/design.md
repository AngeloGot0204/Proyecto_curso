# Design: Wizard de captura server-rendered

## Technical Approach

A new `reportes/` app owns two models (`Reporte`, `ValorDeReporte`) and two FBVs. The wizard is fully data-driven: `reportes/formularios.py::construir_formulario_seccion(seccion)` turns one `estructura["secciones"][i]` into a Django `Form` **class**; `reportes/valores.py` is the string codec between `cleaned_data` and `ValorDeReporte.valor`. Node traversal and value-key naming are **imported from `tipos_reporte`**, never re-derived, so the wizard writes exactly the keys `generador.generar_reporte(definicion, valores)` reads. Implements `specs/reportes-modelo` and `specs/wizard-captura`. Follows ADR-0001 (server-rendered HTML, no frontend framework, no new dependency); no ADR deviation.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| D1 | `ValorDeReporte.valor = TextField(blank=True)`, one canonical string per value | `JSONField` (typed scalars); one column per type | `generador.py` already consumes a `str`→`str` dict (`conftest.valores_completos`: `"08:00"`). One column keeps the generic "one row per field id" contract queryable and migration-free as types grow. |
| D2 | Codec: serialize by dispatching on the **Python value type**; rehydrate with `campo.to_python(texto)` | Hand-written per-`tipo` parser table | Django form fields already parse their own canonical string (`DateField`→ISO, `TimeField`→`HH:MM`, `BooleanField`→`"false"`→`False`, `DecimalField`→`Decimal`). Zero parser to maintain, round-trip proven by the field itself. |
| D3 | Empty submitted value **deletes** its row; `booleano` **always** writes `"true"`/`"false"` | Persist `""` rows for everything | `generador._validar_completitud` uses a *membership* test (its D2), so an `""` row would silently satisfy a required field. Emptiness = "not provided"; unchecked checkbox = a provided `False`. |
| D4 | Reuse `validacion._iterar_nodos({"secciones": [seccion]})` per section | Parallel iterator in `reportes`; parsing its `ubicacion` string | `generador.py` set the precedent (its D1: anchor logic in one place). It also yields `clave_de_etiqueta` (`etiqueta` vs `texto`) — the exact label rule that must not drift. `ubicacion` is a diagnostic format, not an addressing API, so we ignore it. |
| D5 | Extract `generador.claves_de_valor(nodo)` (public) from `_destinos`, import it in `reportes` | Import `_destinos` and discard coordinates; copy `_SUFIJO_POR_CLAVE` | Form field names must equal `ValorDeReporte.identificador_de_campo` must equal generator keys. One suffix map, one owner. `_destinos` would `KeyError` on cell-less nodes; a copy would drift. **Flagged**: a 4-line refactor of `tipos_reporte/generador.py` not listed in the proposal's Affected Areas. |
| D6 | `EstadoDeReporte` = one member, `EN_PROGRESO` | The full TECH-DESIGN lifecycle (5 states); a `cerrado` boolean | Every state past `en progreso` is owned by #7/#9/#10; declaring unreachable states invites premature transitions. `TextChoices` + `CharField` makes adding members purely additive (no column change). |
| D7 | `POST /reportes/<codigo_tipo>/nuevo/` (`require_POST`) creates the `Reporte`, then 302 to section 1 | Lazy creation on the first section's POST | Non-idempotent creation must never happen on GET (refresh/prefetch would spawn orphans). Lazy creation forces an asymmetric first-step URL and a special case in `paso`. Satisfies the spec scenario: `nuevo` **is** the wizard's first submission. |
| D8 | Builder returns a Form **class**; every field is `required=False` | Return an instance; mirror `obligatorio` into `required=True` | The class supports both `Form(initial=…)` (GET) and `Form(data=…)` (POST). Spec "Non-blocking obligatorio marker" requires the deliberate mismatch: HTML `required` attribute on the client, `required=False` on the server (#6 owns blocking). |
| D9 | `get_object_or_404(Reporte, pk=…, creador=request.user)` | 403; a permission class | Creator-only is the whole in-scope rule (#8 expands it). 404 leaks no existence. |
| D10 | App-level `reportes/templates/reportes/` | Project-level `templates/`, as `usuarios` does | `APP_DIRS=True` is already on; the proposal names app-level paths and the wizard shell is app-owned. New convention, not a conflict. |
| D11 | Test fixture builds an already-activated `DefinicionDeTipo` row directly | Call `servicios.activar_definicion` | Activation needs a real `.xlsx` whose merged anchors match every declared cell — that is #3's tested responsibility. The wizard only reads `estructura` and never re-validates. Cost: the fixture must satisfy `definicion_estado_implica_version` itself (`version` + `activada_en` non-null). |

## Data Flow

    POST /reportes/<codigo_tipo>/nuevo/
      └─ Reporte.objects.create(tipo, definicion=tipo.definicion_activa, creador=user)
           └─ 302 → /reportes/<id>/paso/<primera_seccion>/

    GET /reportes/<id>/paso/<sid>/
      estructura[sid] ──_iterar_nodos──▶ construir_formulario_seccion ──▶ Form class
                                                                            │
      ValorDeReporte rows ──campo.to_python()──▶ initial ───────────────▶ Form(initial=)

    POST /reportes/<id>/paso/<sid>/
      Form(data=POST).is_valid() ──cleaned_data──a_texto()──▶ update_or_create | delete
           └─ 302 → next section (last section → itself, PRG)

Navigation: `ids = [s["id"] for s in estructura["secciones"]]` — declaration order **is** wizard order (no `orden` key exists). `sid` not in `ids` → 404. Context carries `pasos` (`id`, `titulo`, `es_actual`), `url_anterior`, `url_siguiente`, `posicion` (`Paso i de n`); the shell renders progress from that list only.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reportes/models.py` | Create | `EstadoDeReporte`, `Reporte`, `ValorDeReporte` |
| `reportes/formularios.py` | Create | `construir_formulario_seccion`, type→field map |
| `reportes/valores.py` | Create | `a_texto` / rehydration helpers (D2) |
| `reportes/views.py` | Create | `iniciar_reporte`, `paso` |
| `reportes/urls.py` | Create | Flat `path()` list, no namespace (`usuarios` convention) |
| `reportes/templates/reportes/paso.html` | Create | Wizard shell + step form, extends `templates/base.html` |
| `reportes/migrations/0001_initial.py` | Create | One migration for both models |
| `reportes/tests/conftest.py`, `tests/test_*.py` | Create | Fixtures + RED tests (strict TDD) |
| `tipos_reporte/generador.py` | Modify | Extract public `claves_de_valor(nodo)` (D5) |
| `config/settings.py`, `config/urls.py` | Modify | Register app; `include('reportes.urls')` |

## Interfaces / Contracts

```python
# reportes/models.py
class Reporte(models.Model):
    tipo = FK(TipoDeReporte, PROTECT, related_name="reportes")
    definicion = FK(DefinicionDeTipo, PROTECT, related_name="reportes")  # version snapshot
    creador = FK(settings.AUTH_USER_MODEL, PROTECT, related_name="reportes_creados")
    fecha_creacion = DateTimeField(auto_now_add=True)
    estado = CharField(max_length=20, choices=EstadoDeReporte.choices,
                       default=EstadoDeReporte.EN_PROGRESO)
    # Invariant (service-enforced, no cross-FK DB constraint possible):
    # definicion.tipo_id == tipo_id. `tipo` is the identity stable across
    # versions; `definicion` is the frozen render/generation contract.

class ValorDeReporte(models.Model):
    reporte = FK(Reporte, CASCADE, related_name="valores")
    identificador_de_campo = CharField(max_length=200)   # == generator key
    valor = TextField(blank=True)
    autor = FK(settings.AUTH_USER_MODEL, PROTECT, related_name="valores_escritos")
    fecha = DateTimeField(auto_now=True)                 # stamps the last upsert
    class Meta:
        constraints = [UniqueConstraint(fields=["reporte", "identificador_de_campo"],
                                        name="valor_unico_por_reporte_y_campo")]
        # DB-level backstop for update_or_create, matching tipos_reporte's
        # convention of constraining invariants in the database too.

def construir_formulario_seccion(seccion: dict) -> type[forms.Form]:
    """type("FormularioDeSeccion", (forms.Form,), campos) — field NAMES are
    exactly generador.claves_de_valor(nodo)."""
```

Type mapping (all `required=False`; `obligatorio` only adds `attrs["required"]` + a visual marker):

| `tipo` | Field name(s) | Form field | Widget | Canonical `valor` |
|---|---|---|---|---|
| `texto` | `{id}` | `CharField` | `TextInput` | as typed |
| `numero` | `{id}` | `DecimalField(localize=False)` | `NumberInput(attrs={"step": "any"})` | `str(Decimal)` — covers ints, no float repr |
| `fecha` | `{id}` | `DateField` | `DateInput(attrs={"type": "date"}, format="%Y-%m-%d")` | ISO `YYYY-MM-DD` |
| `hora` | `{id}` | `TimeField` | `TimeInput(attrs={"type": "time"}, format="%H:%M")` | `HH:MM` |
| `seleccion` | `{id}` | `ChoiceField(choices=[("", "—")] + [(o, o) for o in opciones])` | `Select` | chosen option |
| `booleano` | `{id}` | `BooleanField` | `CheckboxInput` | `"true"` / `"false"` (always written) |
| `rango-hora-inicio-fin` | `{id}_inicio`, `{id}_fin` | two `TimeField` | as `hora` | two rows, `HH:MM` each |

`format=` on `DateInput`/`TimeInput` is mandatory: native `type="date"`/`type="time"` inputs silently drop a non-`%Y-%m-%d`/`%H:%M` value, which would break rehydration (D2). Labels are bound at build time from `clave_de_etiqueta`; range fields get `"{label} — Inicio"` / `"— Fin"`, so the template just iterates the form.

## Testing Strategy

| Layer | What to test | Approach |
|-------|-------------|----------|
| Unit | Codec round-trip per type; `booleano` False persists; empty deletes | `pytest`, no DB where possible |
| Unit | Builder: field names/classes/widgets per type, range→2 fields, empty section→0 fields, `obligatorio`→`attrs["required"]` and still `required=False` | Assert on the returned class's `base_fields` |
| Integration | `nuevo` creates one `Reporte`; GET on `nuevo` is 405; later steps reuse it; foreign `Reporte` → 404; anonymous → 302 to login | `client.force_login` + `reverse(...)` |
| Integration | POST upserts (no duplicate rows on re-POST); GET rehydrates; back/forward preserves data; no session key written | `@pytest.mark.django_db` |
| Contract | `identificador_de_campo` keys equal `generador.claves_de_valor` for the same node | Shared assertion over `definicion_valida` |

Fixtures in `reportes/tests/conftest.py` (app-local duplication is the established convention — `tipos_reporte` duplicates `usuario_factory` deliberately): `usuario_factory` (via `create_user`, so passwords hash), `definicion_valida` (deep-copy factory, mirrored from `tipos_reporte`), `tipo_con_definicion_activa_factory` (creates `TipoDeReporte` + a `DefinicionDeTipo` in activated shape — `estado=ACTIVA`, `version=1`, `activada_en=now` — and points `definicion_activa` at it), `reporte_factory`, `cliente_autenticado` (`client.force_login`; authentication itself is #2's tested concern).

## Threat Matrix

Not applicable. This change adds Django URL patterns only — no shell command, subprocess, VCS/PR automation, executable-file classification, or process integration. Every matrix row (documentation-like paths, git repository selection, commit state, push state, PR commands) is `N/A: no shell or VCS boundary exists in this change`. The real boundaries here are covered by framework defaults and D9: untrusted URL params resolved via `get_object_or_404` scoped to `creador`, CSRF on every POST, and no deserialization of user input (`estructura` comes from an already-validated, admin-uploaded definition).

## Migration / Rollout

One additive migration creating both tables; no existing data touched. Rollback = revert the app, its `INSTALLED_APPS`/`urls.py` registration, and `migrate reportes zero`.

## Open Questions

- [ ] Last step's POST redirects to itself (PRG). A summary/finish screen belongs to #7 — confirm this stop-gap is acceptable UX for #5.
- [ ] D5 touches `tipos_reporte/generador.py`, outside the proposal's Affected Areas — confirm before `sdd-apply`.
