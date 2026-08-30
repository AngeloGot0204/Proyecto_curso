# Design: Mis Reportes (S-02, backlog #12)

## Technical Approach

One new pure module `reportes/listado.py` (query/search/filter helpers, no HTTP —
mirroring `permisos.py`/`valores.py`/`validacion.py`), one thin function view
`reportes/views.py::mis_reportes`, one new URL `reportes/mis/`
(`name="reportes_mis"`), one new template
`reportes/templates/reportes/mis_reportes.html`, and `usuarios/views.py::inicio`
reduced to a redirect. No model, migration, or access-control change: the access
query is reused verbatim from the `_reporte_accesible`/`tiene_acceso` pattern
(backlog #8, design D1) and `permisos.tiene_acceso` is untouched.

**This is the first list/search/pagination screen in the project and is written
as the precedent backlog #13 (admin de tipos de reporte) will copy** — see
"Precedent for #13" below.

## Architecture Decisions

### D1: Routing — new canonical URL, `inicio` becomes a redirect

| Option | Tradeoff |
|---|---|
| Repoint `path("", …, name="inicio")` at `reportes.views.mis_reportes` | `usuarios/urls.py` would import a `reportes` view (cross-app leak), and the list would have no URL under the `reportes/` include for #13 to copy |
| Delete `inicio`, set `LOGIN_REDIRECT_URL = "reportes_mis"` | Breaks `usuarios/tests/test_login.py`'s two `reverse("inicio")` assertions (lines 22, 53) for no functional gain; the root path `/` would 404 |
| **Chosen**: add `reportes/mis/` (`reportes_mis`); `inicio` keeps `name="inicio"`, `@login_required`, and `path("")`, but its body becomes `return redirect("reportes_mis")` | One extra 302 after login; every URL stays in its owning app's URLconf |

`LOGIN_REDIRECT_URL = "inicio"` and `LOGIN_URL = "login"` stay unchanged, so both
existing login/logout tests pass **unmodified**: the login redirect target is
still `reverse("inicio")`, and a logged-out `GET /` still 302s to login because
`inicio` keeps `@login_required`. The redirect is a plain 302, **not** 301 —
a permanent redirect gets cached by browsers and would survive the revert
described in the proposal's rollback plan.

`templates/inicio.html` is deleted (nothing renders it anymore), which makes the
spec's "not the prior placeholder template" assertion structurally true. Its
logout form moves into `mis_reportes.html`; a shared nav in `base.html` is a
deliberate follow-up, not this slice (it would touch `paso`/`revision`/
`participantes` rendering and their substring assertions).

### D2: Page size = 20, `get_page`, one paginator over the combined queryset

| Option | Tradeoff |
|---|---|
| 10 | Forces pagination on users who have a normal week of reports; more round trips on a field-mobile connection |
| 50 / 100 (Django admin default) | A 100-row table on a phone is unusable, and the pagination controls would be untested in practice for every real user |
| **Chosen: 20** (`TAMANO_DE_PAGINA = 20`, module constant in `reportes/views.py`) | Two-to-three phone screens of scrolling; most users never paginate; a 21-report fixture is enough to test page 2 |

Mobile is the primary surface (this app ships a service worker and an offline
capture layer), so page size is chosen for a phone viewport, not a desktop table.

Two sub-decisions ride on this:

- **One `Paginator` over the whole access queryset, grouped inside the page** —
  not two paginators (one per group). Two paginators would need two `?page=`
  params and would destroy the spec's global "most recent first" ordering. The
  view partitions `page_obj.object_list` into `creados`/`compartidos` in Python
  (≤20 rows, no ORM `Case`/`When` needed), so a page may legitimately render an
  empty group.
- **`paginator.get_page(request.GET.get("page"))`, never `paginator.page(...)`** —
  `get_page` clamps `?page=abc` and `?page=999` to a valid page instead of
  raising `PageNotAnInteger`/`EmptyPage` (a 500 or a hand-written 404). Same
  "an optional GET param never blows up the screen" stance as D3.
- **Ordering is `-fecha_creacion, -id`.** The spec fixes `-fecha_creacion`; the
  `-id` tiebreaker is mandatory for *pagination* correctness, since reports
  created in the same transaction share a timestamp and a non-deterministic sort
  makes rows duplicate or vanish across pages. Same tiebreaker rationale as
  backlog #8's `_recortar_historial` (`-fecha, -id`).

### D3: Unrecognized `?estado=` is ignored (unfiltered), never an error

The spec allows exactly two outcomes ("empty **or** unfiltered-by-estado");
400 and redirect are already excluded by it.

| Option | Tradeoff |
|---|---|
| Empty result set (pass the raw value to `filter`) | A stale bookmark or a hand-typed URL renders a blank dashboard indistinguishable from "you have no terminado reports" — looks like data loss, undiagnosable by the user |
| `HttpResponseBadRequest` | Spec-forbidden; and in this codebase `HttpResponseBadRequest` is reserved for POSTs that would corrupt identity (`iniciar_reporte`'s invalid/duplicate `id_local`), never for an optional display filter |
| Redirect without the param | Extra round trip, silently drops `?q=` unless re-encoded, and hides state from the user for no gain |
| **Chosen**: normalize against `EstadoDeReporte.values`; anything unrecognized (or empty) becomes `""` and the estado filter is simply not applied | A typo shows "everything" instead of "nothing" — the safe, self-explanatory failure |

This follows the established server-side leniency of `paso`, where every
generated form field is `required=False` and `form.is_valid()` never blocks. The
normalized value (`""` when invalid) is what goes back into the template's
`<select>`, so the control falls back to "Todos" and never echoes an unusable
value to the user. The `<select>`'s options are rendered from
`EstadoDeReporte.choices`, so the app itself can never emit an invalid value.

### D4: Accent-folded search resolved in Python, no `unaccent` extension

The spec scenario requires `?q=auditoria` to match a type named `"Auditoría"`.
`icontains` compiles to Postgres `ILIKE`, which is case-insensitive but
**accent-sensitive** — `'%auditoria%'` does not match `'Auditoría'`, so the naive
implementation fails that scenario.

| Option | Tradeoff |
|---|---|
| `django.contrib.postgres.lookups.Unaccent` | Needs `CreateExtension("unaccent")` — a migration, which this change explicitly forbids — plus a superuser-capable role on Neon |
| Store a denormalized folded column | New field + migration + backfill; far past this slice |
| **Chosen**: fold accents in Python over `TipoDeReporte`, then `Q(tipo_id__in=…) \| Q(creador__username__icontains=q)` | One extra tiny query; the tipo match does not use an index |

`TipoDeReporte` is a manually administered catalogue of a handful of rows
(backlog #13 is literally its admin screen), so a full scan is free here.
`creador__username` stays on `icontains` because Django's default username
validator is ASCII, so folding buys nothing there.

```python
# reportes/listado.py
def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).casefold()
```

**Tripwire**: if `TipoDeReporte` ever exceeds a few hundred rows, replace this
with `Unaccent` plus a functional index — a deliberate, migration-bearing change.

Search covers `tipo__nombre`, `tipo__codigo` **and** `creador__username`, per the
spec requirement (the change brief abbreviated it to the two `tipo` fields; the
approved spec wins).

## Data Flow

    GET /  ──302──→  GET /reportes/mis/?q=&estado=&page=
                          │
                          ├─ listado.reportes_accesibles(user)
                          │     Reporte.objects.filter(Q(creador=u) | Q(participaciones__usuario=u))
                          │            .distinct().select_related("tipo", "creador")
                          │            .order_by("-fecha_creacion", "-id")
                          ├─ listado.aplicar_busqueda(qs, q)        ← accent-folded (D4)
                          ├─ listado.normalizar_estado(estado) → "" | en_progreso | terminado (D3)
                          ├─ Paginator(qs, 20).get_page(page)       ← clamps bad input (D2)
                          ├─ partition page_obj.object_list → creados | compartidos
                          └─ render reportes/mis_reportes.html

## File Changes

| File | Action | Description |
|---|---|---|
| `reportes/listado.py` | Create | Pure helpers: `reportes_accesibles`, `aplicar_busqueda`, `normalizar_estado`, `_sin_acentos`. No HTTP, no `request` |
| `reportes/views.py` | Modify | `TAMANO_DE_PAGINA = 20`; `mis_reportes` view; module docstring notes the new screen |
| `reportes/urls.py` | Modify | `path("mis/", views.mis_reportes, name="reportes_mis")` (no collision with `<str:codigo_tipo>/nuevo/` — different segment count) |
| `reportes/templates/reportes/mis_reportes.html` | Create | Search form, estado `<select>`, two `<section>` groups, status chip, pagination controls, logout form |
| `usuarios/views.py` | Modify | `inicio` body → `redirect("reportes_mis")`; docstring records that #12 consumed the scope guard |
| `templates/inicio.html` | Delete | No longer rendered; its logout form moves into `mis_reportes.html` |
| `reportes/tests/conftest.py` | Modify | `reportes_para_listar_factory(n, …)` — N reports of varying `tipo`/`estado`/creator |
| `reportes/tests/test_listado.py` | Create | Unit tests for the pure helpers |
| `reportes/tests/test_views.py` | Modify | Integration tests for `mis_reportes` |
| `usuarios/tests/test_login.py` | Modify | **Add** a landing-redirect test; the two existing `reverse("inicio")` tests stay unchanged |

### View shape

```python
@login_required
def mis_reportes(request):
    q = (request.GET.get("q") or "").strip()
    estado = listado.normalizar_estado(request.GET.get("estado"))   # "" when unrecognized
    qs = listado.aplicar_busqueda(listado.reportes_accesibles(request.user), q)
    if estado:
        qs = qs.filter(estado=estado)
    page_obj = Paginator(qs, TAMANO_DE_PAGINA).get_page(request.GET.get("page"))
    creados = [r for r in page_obj if r.creador_id == request.user.id]
    compartidos = [r for r in page_obj if r.creador_id != request.user.id]
    ...
```

`creador_id == request.user.id` is the exact comparison
`participantes.html` already uses, so the grouping rule reuses an existing
in-repo idiom rather than inventing one.

Template details: `{{ reporte.get_estado_display }}` renders the chip, so labels
always come from `EstadoDeReporte` and can never drift (and no `Generacion`
query exists anywhere in this view — the deferred "generado" badge is absent by
construction, not by omission). Pagination links use Django 5.1+'s built-in
`{% querystring page=page_obj.next_page_number %}` tag, which preserves `?q=`
and `?estado=` with zero custom code (`django.template.context_processors.request`
is already enabled). Row links point at `reportes_revision`; a per-estado
destination (resume wizard vs. review) is a follow-up. `numero_registro`/
`id_local` appear nowhere in the template.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `reportes_accesibles` | `test_listado.py`: creator-only, participant-only, both (no duplicate row — proves `.distinct()`), unrelated report excluded |
| Unit | `aplicar_busqueda` | Match by `tipo.nombre`, by `tipo.codigo`, by `creador.username`; `?q=auditoria` matches `"Auditoría"` (accent folding); blank `q` is a no-op |
| Unit | `normalizar_estado` | `"terminado"`/`"en_progreso"` pass through; `""`, `None`, `"basura"`, `"TERMINADO"` → `""` |
| Integration | Access scoping | Creator sees R1, invited sees R2, stranger's R3 absent; staff/admin user sees no unrelated report (no override) |
| Integration | Auth | Anonymous `GET` → 302 to `LOGIN_URL`, no report data in the body |
| Integration | Grouping | Own report under "creados por mí", invited report under "compartidos conmigo" and not in the other group |
| Integration | Chip | `en_progreso` → "En progreso"; `terminado` → "Terminado"; `"generado"` absent from the body |
| Integration | Search/filter | `?q=`, `?estado=`, both combined; `?estado=basura` → 200 with the full unfiltered set (D3) |
| Integration | Pagination/order | 21 reports → page 1 holds 20, `?page=2` holds 1; `?page=abc` and `?page=999` → 200; newest first; `?page=2&q=x` keeps the query string in the links |
| Integration | No `numero_registro` | Populated `numero_registro` does not appear in the rendered body |
| Integration | Landing | `GET reverse("inicio")` → 302 to `reverse("reportes_mis")`; `follow=True` serves the list, and `inicio.html` is not in `response.templates` |

`fecha_creacion` is `auto_now_add=True`, so ordering fixtures must back-date via
`Reporte.objects.filter(pk=…).update(fecha_creacion=…)` — the same technique
backlog #8's `cambios_factory` used for `CambioDeValor.fecha`. The `-id`
tiebreaker (D2) keeps ordering deterministic even without back-dating.

No existing test is rewritten. `test_successful_login_redirects_past_login_screen`
and `test_logout_ends_session_and_redirects_protected_view_to_login` both keep
passing because `inicio` keeps its name, path, and `@login_required`.

## Precedent for #13

Backlog #13 (admin de tipos de reporte) should copy this shape verbatim:

1. Pure `<app>/listado.py`-style helpers for queryset/search/filter — unit-tested
   without HTTP, exactly like `permisos.py`/`valores.py`.
2. Thin `@login_required` function view: read GET params → compose queryset →
   `Paginator(qs, TAMANO_DE_PAGINA).get_page(...)` → render. No class-based
   views; this repo has none.
3. `TAMANO_DE_PAGINA = 20` as the house page size.
4. Optional GET params are normalized and silently ignored when invalid — never
   400, never 500, never an empty screen (D2, D3).
5. Deterministic ordering always carries an `-id` tiebreaker.
6. `{% querystring %}` for pagination links; `{% empty %}` for empty states;
   `<section>` blocks in the `participantes.html` style.

## Threat Matrix

N/A — no shell commands, subprocesses, VCS/PR automation, executable-file
classification, or process integration. Routing changes are plain Django
URLconf entries plus one redirect whose target is a hardcoded named route, so
there is no open-redirect surface (no `?next=`, no user-supplied destination).
The security-relevant surface is authorization, and it is unchanged: the same
creator-or-participant query the wizard already enforces, covered by the access,
auth, and admin-override tests above.

## Migration / Rollout

No migration required — read-only aggregation over existing
`Reporte`/`TipoDeReporte`/`ParticipacionEnReporte` rows. Rollback is a code
revert: restore `inicio`'s `render("inicio.html")` body and
`templates/inicio.html`, drop the URL/view/template/module. The 302 (not 301)
in D1 is what makes that revert take effect immediately for users who already
visited the new screen.

## Known Limitation (documented, not silent)

Administrator override is deliberately absent: a staff/admin user sees only the
reports they created or were invited to, exactly like any other user. The PRD's
admin-intervention edge case remains unaddressed and needs its own capability.

## Open Questions

- [ ] Row destination: this design links every row to `reportes_revision`. An
      `en_progreso` report arguably should resume the wizard at its first
      section instead. Confirm or accept the uniform link.
- [ ] Should the estado `<select>` auto-submit on change, or require an explicit
      "Filtrar" button? The design assumes one plain GET form with a submit
      button (no JS), consistent with the rest of the server-rendered UI.
- [ ] Logout currently moves into `mis_reportes.html`. Promoting it to a shared
      `base.html` nav would serve every screen but touches the existing
      wizard/revision templates — deferred, needs a call.
