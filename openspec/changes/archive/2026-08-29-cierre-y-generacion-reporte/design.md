# Design: Cierre manual (visto bueno) y generación del documento

## Technical Approach

Two additive models (`VistoBueno`, `Generacion`), one additive `EstadoDeReporte` member, one extracted helper, two new POST views, two routes, and a template rewire. No existing behavior changes: `validar_reporte`, `generar_reporte`, and `paso` keep their contracts. Both new views mirror `paso`'s creator-scoped `get_object_or_404` idiom (design D9) except `generar`, which is deliberately not creator-scoped.

## Architecture Decisions

### D1 — `VistoBueno` is `OneToOneField(Reporte)`, not FK

| Option | Tradeoff | Decision |
|---|---|---|
| `OneToOneField` | DB-enforced single closure; gives `reporte.visto_bueno` accessor | **Chosen** |
| `ForeignKey` | Allows a re-close history, needs app-level "latest" logic and an extra query | Rejected |

**Rationale**: visto bueno is a single terminal event per report (ADR-0006), unlike `Generacion` which is an unbounded audit log. Revocation/re-approval is not in scope; adding it later is a `OneToOne`→`FK` migration, not a data loss.

### D2 — Double-POST to `cerrar_reporte` is an idempotent no-op

`get_or_create` inside `transaction.atomic()`. **Rejected**: bare `create()` (raises `IntegrityError` → raw 500 on a double-click, exactly the failure mode the proposal forbids for `generar`) and an explicit 409 (no AC requires it; the user's intent is already satisfied). The success message is emitted either way; `estado` is re-set idempotently.

### D3 — `Generacion` records `definicion` as well as `usuario`/`fecha`

Matches TECH-DESIGN's audit intent: an audit row must say *which template version produced the file*, not only who asked. `Reporte.definicion` is already a snapshot, but the join is one-way and `Generacion` must stay readable if the report is ever re-pointed.

### D4 — `Generar` is *rendered conditionally*, `Cerrar` carries the `disabled` attribute

`revision.html` renders the `Generar` form only when `tiene_visto_bueno`; `Cerrar reporte` is rendered creator-only with `{% if not resultado.puede_generar %}disabled{% endif %}`. **Rejected**: keeping `Generar` always rendered and disabling it without visto bueno — that breaks `test_get_revision_sin_errores_habilita_generar`, which asserts `"disabled" not in response.content.decode()` for a valid, not-yet-closed report. Under the chosen shape, that test still sees no `disabled` (Generar absent, Cerrar enabled), and `test_get_revision_con_errores_deshabilita_generar` still sees `disabled` on Cerrar.

### D5 — `valores_de_reporte` unifies on the related manager

Signature: `def valores_de_reporte(reporte) -> dict[str, str]`, body `return {v.identificador_de_campo: v.valor for v in reporte.valores.all()}`. `validacion.py::validar_reporte` already uses `reporte.valores.all()`; `views.py::paso` uses the equivalent `ValorDeReporte.objects.filter(reporte=reporte)`. Both produce the identical dict, so replacing both call sites is behavior-preserving — `test_validar_reporte_coincide_con_validar_completitud` keeps passing because the *values* fed to `_validar_completitud` are unchanged. `paso` then drops its `ValorDeReporte` import if unused elsewhere.

### D6 — Sentry (ADR-0008) is NOT wired

`config/settings.py` contains no `sentry_sdk` import, no DSN, no `LOGGING` dict; a repo-wide search finds Sentry only in `adrs/0008-*.md`, `TECH-DESIGN.md`, and `BACKLOG.md`. Therefore `generar` MUST log via the stdlib: `logger = logging.getLogger(__name__)` at module level, `logger.exception(...)` in the `except ProblemaDeGeneracion` branch. This is Sentry-ready (the SDK's logging integration picks it up when #14 lands) and useful today without it.

### D7 — Post-closure editing stays open

`paso` is unchanged. A `TERMINADO` report remains editable; nothing locks `ValorDeReporte`. Confirmed by the proposal's question round #3. No task should touch `paso`'s write path.

## Data Flow

    revision (GET) ─→ validar_reporte ─→ puede_generar
         │                                    │
         ├── POST cerrar ─→ 404 unless creador ─→ re-check puede_generar
         │                       └─→ get_or_create(VistoBueno) + estado=TERMINADO ─→ redirect revision
         │
         └── POST generar ─→ any auth user ─→ visto_bueno? ─→ puede_generar?
                                  └─→ valores_de_reporte ─→ generar_reporte(definicion, valores)
                                          ├─ ProblemaDeGeneracion ─→ log + messages.error ─→ redirect revision
                                          └─ BytesIO ─→ Generacion.objects.create ─→ HttpResponse(attachment)

## File Changes

| File | Action | Description |
|---|---|---|
| `reportes/models.py` | Modify | `EstadoDeReporte.TERMINADO`; `VistoBueno`; `Generacion` |
| `reportes/migrations/0002_estado_terminado.py` | Create | `AlterField` on `Reporte.estado` (choices only, no column change) |
| `reportes/migrations/0003_vistobueno_generacion.py` | Create | `CreateModel` × 2 |
| `reportes/valores.py` | Modify | Add `valores_de_reporte` |
| `reportes/validacion.py` | Modify | Call the helper instead of the inline comprehension |
| `reportes/views.py` | Modify | `cerrar_reporte`, `generar`; `paso` + `revision` use the helper; `revision` adds `tiene_visto_bueno`; module `logger` |
| `reportes/urls.py` | Modify | `reportes_cerrar`, `reportes_generar` |
| `reportes/templates/reportes/revision.html` | Modify | Real POST forms with `{% csrf_token %}` |
| `templates/base.html` | Modify | Add the `{% if messages %}` block (absent today) |
| `reportes/tests/conftest.py` | Modify | `plantilla_xlsx`, `reporte_listo_para_cerrar` fixtures |
| `reportes/tests/test_models.py`, `test_valores.py`, `test_views.py` | Modify | New RED tests |

## Interfaces / Contracts

```python
class EstadoDeReporte(models.TextChoices):
    EN_PROGRESO = "en_progreso", "En progreso"
    TERMINADO = "terminado", "Terminado"   # additive; fits max_length=20

class VistoBueno(models.Model):
    reporte = models.OneToOneField(Reporte, on_delete=models.CASCADE, related_name="visto_bueno")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vistos_buenos")
    fecha = models.DateTimeField(auto_now_add=True)

class Generacion(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name="generaciones")
    definicion = models.ForeignKey("tipos_reporte.DefinicionDeTipo", on_delete=models.PROTECT, related_name="generaciones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="generaciones")
    fecha = models.DateTimeField(auto_now_add=True)
```

`on_delete`: `CASCADE` to `Reporte` (audit rows are meaningless without their report, matching `ValorDeReporte`), `PROTECT` to users/definiciones (matches every existing FK in this app).

```python
@login_required
@require_POST
def cerrar_reporte(request, reporte_id):
    reporte = get_object_or_404(Reporte, pk=reporte_id, creador=request.user)
    if not validar_reporte(reporte).puede_generar:
        messages.error(request, "El reporte todavía tiene errores...")
        return redirect("reportes_revision", reporte_id=reporte.id)
    with transaction.atomic():
        VistoBueno.objects.get_or_create(reporte=reporte, defaults={"usuario": request.user})
        reporte.estado = EstadoDeReporte.TERMINADO
        reporte.save(update_fields=["estado"])
    messages.success(request, "Reporte cerrado. Ya puede generarse el documento.")
    return redirect("reportes_revision", reporte_id=reporte.id)
```

`generar`: `@login_required @require_POST`, `get_object_or_404(Reporte, pk=reporte_id)` with **no** `creador` filter (any authenticated user, proposal question #1); redirect to `reportes_revision` with `messages.error` when `VistoBueno` is absent or `puede_generar` is false; `generar_reporte(reporte.definicion, valores_de_reporte(reporte))` inside `try/except ProblemaDeGeneracion`. On success:

```python
nombre = f"{reporte.tipo.codigo}-{reporte.id}-{timezone.localdate():%Y%m%d}.xlsx"
Generacion.objects.create(reporte=reporte, definicion=reporte.definicion, usuario=request.user)
respuesta = HttpResponse(
    buffer.getvalue(),
    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
```

`tipo.codigo` is already a slug-shaped identifier (`instalacion-resinas`), so no extra sanitization is needed for the header.

**Non-creator caveat**: `revision` stays creator-scoped, so a non-creator can only reach `generar` by direct POST, and its error redirect lands on a 404 for them. Accepted for this slice (the UI entry point is creator-visible only); opening `revision` belongs to backlog #8.

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | `valores_de_reporte` | `test_valores.py`: rows in → exact dict out; empty report → `{}` |
| Unit | `VistoBueno`/`Generacion` | `test_models.py`: field defaults, `auto_now_add`, second `VistoBueno` raises `IntegrityError`, N `Generacion` rows allowed |
| Integration | `cerrar_reporte` | 404 for non-creator; blocked when `errores`; sets `TERMINADO`; double-POST leaves exactly 1 row and no 500 |
| Integration | `generar` | 302 + `messages` error without `VistoBueno`; 302 + error on `ProblemaDeGeneracion` (never 500); one `Generacion` row per success; two POSTs → two rows |
| Integration | download | see fixture/assertion pattern below |
| Integration | template | Generar form absent before closure, present after; Cerrar hidden for non-creator |

**Fixtures.** Add to `reportes/tests/conftest.py` (app-local duplication is this repo's stated convention): a `plantilla_xlsx(tmp_path)` factory mirroring `tipos_reporte/tests/conftest.py`'s — the existing `tipo_con_definicion_activa_factory` uploads `b"contenido-irrelevante-para-este-nivel"`, which `load_workbook` cannot parse, so generation tests **must** pass a real workbook through the `plantilla=` kwarg. Add `reporte_listo_para_cerrar` returning `(client, reporte)` with `estructura_con_validaciones`, a real template, the creador logged in, and all four obligatorio `ValorDeReporte` rows persisted (`observaciones-generales`, `estado-general="Cumple"`, `p-01_inicio="08:00"`, `p-01_fin="09:00"`) — i.e. `puede_generar` is true. Cells must exist in the template: build it with `rangos=("M10:P10", "M12:P12", "M25:P25")`.

**Download assertions (first of their kind in this repo).**

```python
assert response.status_code == 200
assert response["Content-Type"] == (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
esperado = f"{reporte.tipo.codigo}-{reporte.id}-{timezone.localdate():%Y%m%d}.xlsx"
assert response["Content-Disposition"] == f'attachment; filename="{esperado}"'
libro = load_workbook(BytesIO(response.content))
assert libro.sheetnames == ["REPORTE"]
assert libro["REPORTE"]["M10"].value == "Todo en orden."
assert libro["REPORTE"]["M25"].value == "08:00"
```

Flash messages are read with `list(get_messages(response.wsgi_request))` and asserted on `.level`/presence, never on exact prose.

## Threat Matrix

N/A — no routing beyond two ordinary Django URL patterns, no shell, subprocess, VCS/PR automation, or executable-file classification. The generated `.xlsx` is served as an attachment with a fixed, server-derived filename (never user-supplied), so no header-injection or content-sniffing surface is introduced.

## Migration / Rollout

Two additive migrations, no backfill: `0002` only rewrites `choices` metadata (no DDL on Postgres for a `CharField` without `db_check`), `0003` creates two empty tables. Rollback is `migrate reportes 0001` plus reverting the code. Existing `Reporte` rows keep `estado="en_progreso"`.

## ADR Deviations

None. ADR-0006 (creator closes, collaboration open) and ADR-0002 (generation) are followed. ADR-0008's Sentry expectation is *unmet in code today* (D6) — flagged, not deviated from, since #14 owns that wiring.

## Open Questions

- [ ] None blocking. Revocation of a `VistoBueno` and locking values after closure are both deferred (proposal questions #2/#3).
