# Design: Colaboración por invitación y edición abierta

## Technical Approach

Two additive models (`ParticipacionEnReporte`, `CambioDeValor`) in migration `0004`, one new HTTP-free predicate module `reportes/permisos.py`, one private view shim `_reporte_accesible`, two new views (`invitar`, `participantes`) with a new S-10 template, and a refactor of `guardar_valor` into a single `transaction.atomic()` that does read-before-write, the existing upsert/delete, the audit insert, and the FIFO-30 trim. No existing module boundary moves: `permisos.py` mirrors `valores.py`/`validacion.py` (pure domain, no HTTP), the 404 shim lives in `views.py` beside `_seccion_por_id`/`_url_paso`.

## Architecture Decisions

### D1: Access check = fetch-then-check-then-404, not a filtered queryset

| Option | Tradeoff |
|---|---|
| `Reporte.objects.filter(Q(creador=u) \| Q(participaciones__usuario=u)).distinct()` into `get_object_or_404` | Join fan-out needs `.distinct()` or `get_object_or_404` raises `MultipleObjectsReturned` (500); predicate is not reusable outside a queryset |
| **Chosen**: `get_object_or_404(Reporte, pk=…)` then `if not tiene_acceso(...): raise Http404` | Same 404 for "absent" and "no access" → preserves D9's no-existence-leak; `tiene_acceso` is unit-testable without HTTP and reusable in template context |

`get_object_or_404` cannot take an arbitrary boolean, and it itself only ever raises `Http404` — raising `Http404` manually produces a byte-identical response. `views.py` already raises `Http404` directly in `iniciar_reporte`/`paso`, so this is the established pattern.

```python
# reportes/permisos.py — pure predicate
def tiene_acceso(reporte, usuario) -> bool:
    if not usuario.is_authenticated:      # defensive; all callers are @login_required
        return False
    if reporte.creador_id == usuario.id:  # creator has no participation row (ADR-0006)
        return True
    return ParticipacionEnReporte.objects.filter(
        reporte=reporte, usuario=usuario
    ).exists()

# reportes/views.py — private 404 shim, used by paso, revision, generar, participantes
def _reporte_accesible(reporte_id, usuario):
    reporte = get_object_or_404(Reporte, pk=reporte_id)
    if not tiene_acceso(reporte, usuario):
        raise Http404("Reporte inexistente o sin acceso.")
    return reporte
```

`cerrar_reporte` and `invitar` keep the strict `get_object_or_404(Reporte, pk=…, creador=request.user)` — they are creator-only, never `tiene_acceso`.

### D2: `UniqueConstraint` instead of literal `unique_together`

The spec says `unique_together(reporte, usuario)`; `ValorDeReporte` already uses `Meta.constraints = [UniqueConstraint(...)]`, which is Django's recommended form and semantically identical. **Deviation flagged**: implemented as `UniqueConstraint(fields=["reporte","usuario"], name="participacion_unica_por_reporte_y_usuario")`, satisfying the requirement's intent. `makemigrations` emits `CreateModel` + a separate `AddConstraint` operation.

### D3: `valor_anterior` is `TextField(blank=True, null=True)`

`NULL` means "no prior row existed" (first write). `""` is impossible in `ValorDeReporte` (design D3 deletes empty values), so `NULL` is the only way to express first-write and never collides with a real stored value.

### D4: Audit rows only on *actual* changes

`guardar_valor` short-circuits when (a) the value is empty and no row exists, or (b) the serialized value equals the stored one. This is load-bearing, not an optimization: `paso`'s POST loop calls `guardar_valor` for **every** field in the section on every submit, so without the guard a single step POST would burn the whole 30-row budget with no-ops. Side effect: an unchanged resubmit no longer bumps `ValorDeReporte.fecha`/`autor`. No existing test asserts that.

### D5: FIFO-30 trim via materialized `pk__in`, no row lock

```python
def _recortar_historial(reporte):
    sobrantes = list(
        CambioDeValor.objects.filter(reporte=reporte)
        .order_by("-fecha", "-id")            # -id breaks fecha ties deterministically
        .values_list("pk", flat=True)[30:]    # slice = OFFSET 30, keeps newest 30
    )
    if sobrantes:
        CambioDeValor.objects.filter(pk__in=sobrantes).delete()
```

- **Correct**: Django forbids `.delete()` on a sliced queryset; `pk__in` sidesteps it. `-fecha` alone is non-deterministic when a step POST writes several fields inside the same microsecond, hence the `-id` tiebreaker.
- **Efficient**: filtered by the automatic `reporte_id` FK index, then ≤31 rows sorted. No extra composite index needed at this cardinality.
- **`list(...)` vs. raw subquery**: passing the sliced queryset directly builds `DELETE … WHERE pk IN (SELECT … FROM cambiodevalor LIMIT/OFFSET)`; Postgres allows self-referencing subselects but MySQL does not. Materializing costs one cheap extra query and is backend-agnostic.
- **Concurrency**: `transaction.atomic()` at READ COMMITTED does not serialize two concurrent writers on the same `Reporte`; each may compute the same excess set (the second `DELETE` is a harmless no-op) or, if inserts are mutually invisible, leave 31 rows transiently — self-healed by the next write. FIFO-30 is a retention policy, not a safety invariant, so a `Reporte`-row `select_for_update()` is deliberately rejected to keep the hot wizard path lock-free. Documented, not accidental.

### D6: New `participantes` view/template, not an extension of `revision.html`

S-10 is a distinct DESIGN screen, and `revision.html` is asserted against by substring in existing tests — `test_get_revision_sin_errores_habilita_generar` asserts `"disabled" not in response.content`, so any new control there is a latent breakage. `revision.html` gains only a plain `<a href="{% url 'reportes_participantes' … %}">` link.

## Data Flow

    POST paso ──→ guardar_valor ──┬─ read ValorDeReporte (valor_anterior | None)
                                  ├─ no-op? → return (no history)
       transaction.atomic()       ├─ upsert / delete ValorDeReporte
                                  ├─ INSERT CambioDeValor
                                  └─ _recortar_historial(reporte)  → keep newest 30

    GET participantes ──→ _reporte_accesible ──→ ParticipacionEnReporte(select_related usuario)
                                              └→ CambioDeValor(select_related autor, -fecha,-id)
    POST invitar (creador only) ──→ Usuario.filter(username=…).first()
                                 └→ get_or_create(reporte, usuario) → messages → redirect

## Interfaces / Contracts

```python
class ParticipacionEnReporte(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE,
                                related_name="participaciones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="participaciones")
    fecha_invitacion = models.DateTimeField(auto_now_add=True)
    # Meta.constraints: UniqueConstraint(["reporte","usuario"],
    #   name="participacion_unica_por_reporte_y_usuario")

class CambioDeValor(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE,
                                related_name="cambios")
    identificador_de_campo = models.CharField(max_length=200)   # matches ValorDeReporte
    valor_anterior = models.TextField(blank=True, null=True)    # NULL = first write
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="cambios_de_valor")
    fecha = models.DateTimeField(auto_now_add=True)             # immutable, not auto_now
```

No `Meta.ordering` on either model (no existing model declares one); call sites order explicitly.

`guardar_valor(reporte, identificador_de_campo, valor, autor)` keeps its exact signature and both existing behaviours (empty deletes, non-empty upserts). `transaction.atomic()` stays *inside* `guardar_valor` so `test_valores.py`'s direct calls need no wrapper; a future `atomic()` around `paso`'s loop would nest as a savepoint, which is compatible.

## File Changes

| File | Action | Description |
|---|---|---|
| `reportes/models.py` | Modify | Add `ParticipacionEnReporte`, `CambioDeValor`; fix `Generacion` docstring ("any authenticated user" → participant-scoped) |
| `reportes/migrations/0004_participacion_cambiodevalor.py` | Create | 2× `CreateModel` + `AddConstraint`; deps `0003_vistobueno_generacion` + `swappable_dependency(AUTH_USER_MODEL)` |
| `reportes/permisos.py` | Create | `tiene_acceso(reporte, usuario) -> bool` |
| `reportes/valores.py` | Modify | `guardar_valor` transaction refactor + `_recortar_historial` |
| `reportes/views.py` | Modify | `_reporte_accesible`; `paso`/`revision`/`generar` switch to it; add `invitar`, `participantes`; update module docstring (currently states creator-only D9) |
| `reportes/urls.py` | Modify | `reportes_participantes`, `reportes_invitar` |
| `reportes/templates/reportes/participantes.html` | Create | Creator label, invited list, creator-only invite form, history table |
| `reportes/templates/reportes/revision.html` | Modify | Link to participantes (plain `<a>`, no `disabled` substring) |
| `reportes/tests/conftest.py` | Modify | `participacion_factory`, `reporte_con_participantes_factory`, `cambios_factory` |
| `reportes/tests/test_permisos.py` | Create | Unit tests for `tiene_acceso` |
| `reportes/tests/test_valores.py` | Modify | History + FIFO-30 boundary tests |
| `reportes/tests/test_views.py` | Modify | Participant-access, invite, participantes tests; rewrite one `generar` test (see below) |

### Invite view shape

```python
@login_required
@require_POST
def invitar(request, reporte_id):
    reporte = get_object_or_404(Reporte, pk=reporte_id, creador=request.user)
    username = (request.POST.get("username") or "").strip()
    invitado = get_user_model().objects.filter(username=username).first()
    if invitado is None:
        messages.error(request, f"No existe un usuario con el nombre «{username}».")
    elif invitado.id == reporte.creador_id:
        messages.error(request, "El creador ya tiene acceso al reporte.")
    else:
        ParticipacionEnReporte.objects.get_or_create(reporte=reporte, usuario=invitado)
        messages.success(request, f"{username} ya puede trabajar en este reporte.")
    return redirect("reportes_participantes", reporte_id=reporte.id)
```

`get_or_create` gives idempotency without relying on catching `IntegrityError`, mirroring `cerrar_reporte`'s `get_or_create`. The self-invite branch is **not** in the spec; it exists to protect the "creator has no participation row" invariant (see Open Questions).

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `tiene_acceso` | `test_permisos.py`: creator True, invited True, stranger False, anonymous False |
| Unit | `guardar_valor` audit + FIFO | `test_valores.py`: first write → `valor_anterior is None`; overwrite → prior text; delete-of-existing → row written; no-op delete and unchanged resubmit → zero rows; 30 writes → 30 rows; 31st → still 30 and the oldest pk gone; FIFO spans multiple fields |
| Integration | Access | `paso`/`revision`/`generar` as invited participant → 200; as stranger → 404; `cerrar_reporte` as invited participant → 404 (still creator-only) |
| Integration | Invite | success creates row + success message; unknown username → error message, zero rows; double invite → exactly 1 row; non-creator POST → 404 |
| Integration | Participantes | lists invited usernames, shows creator label, history newest-first, invite form only for creator |

### Fixture strategy

- `participacion_factory(db, usuario_factory)` → `_crear(reporte, username="invitado")` creates the `Usuario` **and** its `ParticipacionEnReporte`, returns the user. Explicit `username` per call, following the existing convention that avoids `"usuario_test"` collisions with `cliente_autenticado`.
- `sesion_de_invitado` (local to `test_views.py`, mirroring `sesion_de_creador`) → `(client, reporte)` logged in as an invited non-creator.
- `reporte_con_participantes_factory` → reporte + N invited users, usernames `invitado_0..N-1`.
- `cambios_factory(reporte, n, autor)` → creates N `CambioDeValor` rows, then back-dates `fecha` with `queryset.update(fecha=…)`, since `auto_now_add` ignores values passed to `create()`. The `-id` tiebreaker makes ordering deterministic even without back-dating.

### Existing tests: coexistence and the one required rewrite

Pass **unchanged** (a stranger is neither creator nor participant, so 404 still holds): `test_paso_reporte_de_otro_usuario_da_404`, `test_get_revision_reporte_de_otro_usuario_da_404`, `test_cerrar_reporte_no_creador_devuelve_404`, `test_get_revision_no_creador_no_ve_boton_cerrar` (renders the template directly, no access check). All `reporte_listo_para_cerrar`-based `generar` tests keep passing because that fixture logs in the **creator**.

**Exactly one test asserts #7's "any authenticated user succeeds":** `reportes/tests/test_views.py::test_generar_no_creador_tambien_puede_generar` (lines 593–609), whose comment cites spec requirement *"Any Authenticated User May Generate"*. It is the sole reversal casualty. It must be **rewritten, not deleted**, splitting its intent in two:

1. `test_generar_participante_invitado_es_exitoso` — same body plus `ParticipacionEnReporte.objects.create(reporte=reporte, usuario=otro)` before the POST; keeps the original `status_code == 200` and `Generacion.usuario == otro` assertions. Preserves "a non-creator can generate."
2. `test_generar_no_participante_devuelve_404` — original body unchanged, asserting `404` and `not Generacion.objects.filter(reporte=reporte).exists()`. Captures the new restriction.

## Threat Matrix

N/A — no routing beyond Django URLconf entries, no shell commands, subprocesses, VCS/PR automation, executable-file classification, or process integration. The security-relevant surface (authorization) is covered by the access-control tests above.

## Migration / Rollout

Additive only: two new tables, no column change, no data backfill. `CambioDeValor` starts empty, so pre-existing reports simply show an empty history. Rollback = `migrate reportes 0003` + revert `views.py`/`valores.py`/`urls.py`/templates.

## Open Questions

- [ ] Delta specs are missing for the two reversed/widened requirements: `openspec/specs/generacion-documento/spec.md` → *"Any Authenticated User May Generate"* needs a `MODIFIED`/`RENAMED` delta, and `wizard-captura`'s Out-of-Scope line 119 ("creator-only access") plus `validacion-reporte`'s S-09 requirement need widening. Only `specs/colaboracion-reporte/spec.md` exists in this change.
- [ ] Self-invite: the spec is silent; this design rejects it with a flash message to protect "creator has no participation row." Confirm or drop the branch.
- [ ] Should a participant be removable from a report? Not in scope for #8; no `desinvitar` action is designed.
