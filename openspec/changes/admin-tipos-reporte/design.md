# Design: Administración de tipos de reporte (S-14, backlog #13)

## Technical Approach

A thin, server-rendered screen over logic that already exists. Net-new:
`tipos_reporte/listado.py` (pure query helpers, copied from backlog #12's
`reportes/listado.py`), `tipos_reporte/views.py`, `tipos_reporte/urls.py`,
`tipos_reporte/forms.py`, four templates under
`tipos_reporte/templates/tipos_reporte/`, and one new
`usuarios/decorators.py::solo_administradores`. `servicios.py`
(`activar_definicion`/`desactivar_tipo`) and `generador.py`
(`_intercambiar_logo`) are called, never edited. `validacion.py` gains
exactly one function — the YAML-upload parser extracted verbatim from
`admin.py::DefinicionDeTipoForm.clean()`. No model, no migration.

Delivered as two stacked-to-main PRs, the #10/#11/#12 pattern:

| PR | Scope |
|---|---|
| **PR1** | `usuarios/decorators.py::solo_administradores`, `listado.py`, `urls.py`, list + detail views, activate/desactivate POST routes, `lista.html`/`detalle.html`. All gated by the decorator (D1) from the start. |
| **PR2** | `forms.py`, create/edit views + templates for both models, `validacion.py::analizar_definicion_subida` extraction, `admin.py` deregistration. |

## Architecture Decisions

### D1 — `usuarios/decorators.py::solo_administradores`, `login_required` outermost

`usuarios/decorators.py` does not exist; it is created here.
`Usuario.es_administrador` is a **property** (`usuarios/models.py:41`)
returning `self.rol == Rol.ADMINISTRADOR` — no arguments, so it composes
directly into a predicate.

| Option | Tradeoff |
|---|---|
| `@user_passes_test(lambda u: u.es_administrador)` | Redirects an authenticated non-admin back to `LOGIN_URL` — a login loop for a user who is already logged in, and it violates the spec's explicit 403 requirement |
| `@staff_member_required` | Gates on `is_staff`, which `usuarios` design D1 documents as a *derived mirror* of `rol`, not the source of truth; it would also bounce to the admin login form |
| Per-view inline `if not request.user.es_administrador: raise PermissionDenied` | Six copies of the same guard; the spec requires "a new decorator … MUST be the single gating mechanism" |
| **Chosen**: `solo_administradores`, `login_required` applied *outermost* | One extra module; anonymous users never reach the property access |

```python
# usuarios/decorators.py
def solo_administradores(vista):
    """Single gating mechanism for the tipos-de-reporte screen (spec
    "Admin-Role-Gated Access"). `login_required` is applied LAST, so it
    wraps the role check: an anonymous request is redirected to
    `LOGIN_URL` before `request.user.es_administrador` is ever read
    (`AnonymousUser` has no such attribute)."""
    @wraps(vista)
    def _envoltura(request, *args, **kwargs):
        if not request.user.es_administrador:
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return login_required(_envoltura)
```

`PermissionDenied` → Django's `handler403` → 403 with no view body executed,
satisfying "MUST NOT execute its normal body or expose any data". The repo
has no custom `403.html`, so Django's built-in page is served; adding one is
out of scope.

**PR boundary note**: PR1 already needs the gate. The decorator therefore
ships in **PR1**, not PR2 — the locked PR split lists it under PR2's
"admin-role decorator", but PR1's views cannot be spec-compliant without it,
and shipping an inline duplicate in PR1 would violate the spec's
"single gating mechanism" clause. Flagged in Open Questions.

### D2 — Shared YAML helper lives in `validacion.py`, not `servicios.py`

| Option | Tradeoff |
|---|---|
| `servicios.py` | That module is DB-mutating orchestration: every function opens `transaction.atomic()` and writes rows. A pure byte-decoding parser has no business there |
| **Chosen: `validacion.py`** | Already the home of `analizar_yaml_seguro` (the `yaml.safe_load` wrapper this helper calls), already pure (no DB, no HTTP), already the app's declared "untrusted deserialization" boundary |
| New `tipos_reporte/parseo.py` | A third module for one function; no precedent for splitting validation across files |

```python
# tipos_reporte/validacion.py
def analizar_definicion_subida(archivo) -> tuple[str, dict]:
    """UTF-8 decode → `analizar_yaml_seguro` → dict-root check →
    JSON-representability check, over an uploaded/stored definition file.
    Returns `(yaml_fuente, estructura)`. Raises Django's `ValidationError`
    keyed on `"archivo_yaml"` — the DefinicionDeTipo MODEL field name, so
    the key is domain-level, not form-level."""
```

The body is `admin.py:64-92` moved verbatim (same four checks, same four
Spanish messages), minus the `archivo is None` guard and the `cleaned[...]`
assignments, which stay at each call site. Raising `ValidationError` rather
than returning `ProblemaDeDefinicion`s is deliberate: this is a *fail-fast
upload gate* ("can this become a JSON document?", design D4), not the
accumulating activation gate (R1–R7), and `models.py` already raises
`django.core.exceptions.ValidationError` from this app. Both `admin.py`'s
form (until its PR2 deregistration) and the new form become one line:

```python
cleaned["yaml_fuente"], cleaned["estructura"] = analizar_definicion_subida(archivo)
```

### D3 — List view copies backlog #12's pattern verbatim

This is the **second** list/pagination screen; #12's design named itself the
precedent to copy, and this design copies all six of its rules: pure
`listado.py` helpers, thin `@`-decorated function view (no CBVs — this repo
has none), `TAMANO_DE_PAGINA = 20`, `Paginator(...).get_page(...)` (clamps
`?page=abc`/`?page=999` instead of raising), deterministic ordering with an
id tiebreaker, and `{% querystring %}` pagination links.

**One documented deviation**: `_sin_acentos` is *duplicated* into
`tipos_reporte/listado.py` rather than imported from `reportes.listado`.
`tipos_reporte` must not import `reportes` (dependency direction, stated in
backlog #11's design D5 — `generador.py` takes attachments by injection for
exactly this reason). Extracting three lines into a new shared package would
also force an edit to #12's merged module. The duplication carries a comment
naming its twin.

Ordering is `("nombre", "id")` — alphabetical for a hand-curated catalogue,
with the mandatory `id` tiebreaker. Search folds accents over `nombre` and
`codigo` in Python, same `TipoDeReporte`-is-tiny rationale and same tripwire
as #12's D4.

### D4 — `plantilla` read-only via `disabled=True`

| Option | Tradeoff |
|---|---|
| Reject a changed `plantilla` in `clean()` | Spec forbids it: "MUST render `plantilla` as read-only (not merely reject a changed value after the fact)" |
| `del self.fields["plantilla"]` | The field disappears entirely; the admin cannot even see which template is bound |
| **Chosen**: `self.fields["plantilla"].disabled = True` when `instance.definicion_activa_id is not None` | Django renders the `disabled` attribute *and* `BaseForm._clean_fields` substitutes the initial value for any POSTed one, so a hand-crafted POST cannot persist a change |

This is the direct port of `TipoDeReporteAdmin.get_readonly_fields`'s
`obj.definicion_activa_id is not None` condition (`admin.py:149`) into form
terms.

### D5 — `DefinicionDeTipoForm` narrows `fields`; edit is borrador-only

The new form declares `fields = ("archivo_yaml",)`. That single change
dissolves the workaround `admin.py`'s form needs: with `fields = "__all__"`,
`yaml_fuente`/`estructura` are model-required form fields that Django's
`_clean_fields()` rejects *before* `clean()` can derive them, which is why
admin's `__init__` flips both to `required=False`. Outside the form,
`_get_validation_exclusions` skips them, so derivation happens on the
instance:

```python
self.instance.yaml_fuente, self.instance.estructura = analizar_definicion_subida(archivo)
```

`tipo` is fixed by the URL (`form.instance.tipo = tipo` before
`is_valid()`), and `estado`/`version`/`activada_en` are absent from the form
entirely — they change only through `servicios.activar_definicion`
(design D8), satisfying the spec's "not administrator-editable".

**Edit is restricted to `estado == BORRADOR`.** `models.py`'s `CONGELADOS`
guard makes `estructura`/`yaml_fuente` immutable once a row leaves borrador,
so an edit form for an `activa`/`historica` row could only ever raise
`ValidationError` from `save()`. The edit view returns 404 for a non-borrador
row; the detail screen renders those rows read-only. This is an honest read
of the model invariant, not extra scope.

### D6 — Activate/desactivate are POST-only, PRG + `messages`

`@require_POST` (already used by `subir_adjunto`) plus CSRF, then
`redirect` back to the detail view — the Post/Redirect/Get + `messages`
idiom every mutating view in this repo uses. Activation surfaces one
`messages.ERROR` per `ProblemaDeDefinicion`, rendered `"{ubicacion}:
{mensaje}"`, byte-identical to `DefinicionDeTipoAdmin.activar`
(`admin.py:128-133`). GET routes would make these CSRF-less state changes
reachable from a prefetch or a link.

### D7 — Deregistration removes the two `@admin.register(...)` lines only

| Option | Tradeoff |
|---|---|
| Delete `admin.py`'s ModelAdmin/form classes outright | ~170 deleted lines plus a 367-line `test_admin.py` rewrite in a PR that is already the heavy half of the chain, and it contradicts the approved proposal's rollback plan |
| `admin.site.unregister(...)` after registering | Registers then immediately unregisters — noise, not clarity |
| **Chosen**: delete the two `@admin.register(DefinicionDeTipo)` / `@admin.register(TipoDeReporte)` decorator lines; keep the classes and their tests | Rollback is exactly the proposal's stated "one-line-per-model revert"; `test_admin.py` keeps passing unchanged because every test constructs `DefinicionDeTipoAdmin(DefinicionDeTipo, AdminSite())` directly and none asserts on `admin.site._registry` |

`admin.py`'s module docstring gains a paragraph recording that the classes
are retained deliberately as a one-line-revert rollback path, and that the
live surface is now `tipos_reporte/urls.py`. Retiring them for good is a
follow-up.

### D8 — No new upload validators

`logo` keeps `ImageField`'s built-in Pillow decodability check (already
covered by two `test_admin.py` tests); `plantilla` and `archivo_yaml` keep
plain `FileField` with zero size/format checks. `reportes/adjuntos.py`'s
allowlist/ceiling is **not** reused — the spec's "No Size or Format Ceiling"
requirement makes this a non-requirement, and the contrast (trusted admin vs.
end-user upload) is the documented reason.

Logo-keep-on-no-reupload needs **no code**: the plain `ModelForm` +
`ClearableFileInput` default already leaves `instance.logo` untouched when no
file is posted. `generador.py::_intercambiar_logo` (confirmed at
`tipos_reporte/generador.py:117`, not `reportes/`) is not touched; its
empty-logo/leave-template-default branch gets a regression test only.

## Data Flow

    GET /tipos-reporte/?q=&page=          [solo_administradores]
      ├─ anónimo ──302──▶ LOGIN_URL
      ├─ rol != administrador ──▶ PermissionDenied ──▶ 403
      └─ administrador
           ├─ listado.tipos_administrables()           TipoDeReporte
           │      .select_related("definicion_activa").order_by("nombre","id")
           ├─ listado.aplicar_busqueda(qs, q)          ← accent-folded (D3)
           ├─ Paginator(qs, 20).get_page(?page)        ← clamps bad input
           └─ render tipos_reporte/lista.html

    GET /tipos-reporte/<id>/  ──▶ tipo + tipo.definiciones
                                   .order_by(F("activada_en").desc(nulls_first=True), "-id")
                                 ──▶ detalle.html  (borrador arriba)

    POST /tipos-reporte/definiciones/<id>/activar/        [require_POST]
      └─ servicios.activar_definicion(definicion)   ← sin cambios
           ├─ ResultadoDeValidacion.es_valida ──▶ messages.SUCCESS
           └─ problemas ──▶ un messages.ERROR por ProblemaDeDefinicion
      └─ 302 ▶ detalle

    POST /tipos-reporte/<id>/desactivar/                  [require_POST]
      └─ servicios.desactivar_tipo(tipo)  ── sin cambios ──▶ 302 ▶ detalle

    POST /tipos-reporte/<id>/definiciones/nueva/          (PR2)
      └─ DefinicionDeTipoForm.clean()
           └─ validacion.analizar_definicion_subida(archivo)
                 UTF-8 ▸ analizar_yaml_seguro ▸ dict-root ▸ json.dumps
                 ├─ falla ──▶ ValidationError{"archivo_yaml"} ──▶ 200 + error de campo
                 └─ ok ──▶ instance.yaml_fuente / instance.estructura ──▶ borrador
      (mismo helper que admin.py::DefinicionDeTipoForm.clean hasta PR2)

## File Changes

| File | Action | PR | Description |
|---|---|---|---|
| `usuarios/decorators.py` | Create | 1 | `solo_administradores` (D1) |
| `tipos_reporte/listado.py` | Create | 1 | `tipos_administrables`, `aplicar_busqueda`, `_sin_acentos` (D3) |
| `tipos_reporte/views.py` | Create | 1 | `TAMANO_DE_PAGINA = 20`; `lista`, `detalle`, `activar_definicion_vista`, `desactivar_tipo_vista` |
| `tipos_reporte/urls.py` | Create | 1 | 8 routes (4 in PR1, 4 in PR2) |
| `config/urls.py` | Modify | 1 | `path("tipos-reporte/", include("tipos_reporte.urls"))` |
| `tipos_reporte/templates/tipos_reporte/lista.html` | Create | 1 | Search form, table, `{% querystring %}` pagination |
| `tipos_reporte/templates/tipos_reporte/detalle.html` | Create | 1 | Tipo fields, definición history, activate/desactivate POST forms |
| `tipos_reporte/validacion.py` | Modify | 2 | `analizar_definicion_subida` (D2) |
| `tipos_reporte/forms.py` | Create | 2 | `TipoDeReporteForm` (D4), `DefinicionDeTipoForm` (D5) |
| `tipos_reporte/views.py` | Modify | 2 | `crear_tipo`, `editar_tipo`, `crear_definicion`, `editar_definicion` |
| `tipos_reporte/templates/tipos_reporte/formulario_tipo.html` | Create | 2 | `enctype="multipart/form-data"` |
| `tipos_reporte/templates/tipos_reporte/formulario_definicion.html` | Create | 2 | `enctype="multipart/form-data"` |
| `tipos_reporte/admin.py` | Modify | 2 | Two `@admin.register(...)` lines removed; docstring records why (D7) |
| `usuarios/tests/test_decorators.py` | Create | 1 | Decorator unit/integration tests |
| `tipos_reporte/tests/test_listado.py` | Create | 1 | Pure-helper unit tests |
| `tipos_reporte/tests/test_vistas.py` | Create | 1→2 | View integration tests, extended in PR2 |
| `tipos_reporte/tests/test_formularios.py` | Create | 2 | Form + shared-helper tests |
| `tipos_reporte/tests/test_generador.py` | Modify | 2 | Empty-logo regression test |
| `tipos_reporte/tests/conftest.py` | Modify | 1 | `administrador_factory`, `definicion_factory` |

## Interfaces / Contracts

| Route name | Path | Method | Notes |
|---|---|---|---|
| `tipos_lista` | `/tipos-reporte/` | GET | `?q=`, `?page=` |
| `tipos_detalle` | `/tipos-reporte/<int:tipo_id>/` | GET | |
| `tipos_desactivar` | `/tipos-reporte/<int:tipo_id>/desactivar/` | POST | |
| `tipos_definicion_activar` | `/tipos-reporte/definiciones/<int:definicion_id>/activar/` | POST | |
| `tipos_crear` | `/tipos-reporte/nuevo/` | GET, POST | PR2 |
| `tipos_editar` | `/tipos-reporte/<int:tipo_id>/editar/` | GET, POST | PR2 |
| `tipos_definicion_crear` | `/tipos-reporte/<int:tipo_id>/definiciones/nueva/` | GET, POST | PR2 |
| `tipos_definicion_editar` | `/tipos-reporte/<int:tipo_id>/definiciones/<int:definicion_id>/editar/` | GET, POST | PR2, borrador only (D5) |

`nuevo/` cannot shadow `<int:tipo_id>/` — the converter rejects it. Every
route carries `solo_administradores`.

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | `solo_administradores`: admin passes; non-admin → `PermissionDenied`; anonymous → 302 to `LOGIN_URL` **before** the property is read | `RequestFactory` + `AnonymousUser`, no DB for the anonymous case |
| Unit | `tipos_administrables` ordering (`nombre`, `id` tiebreaker), `select_related` | `test_listado.py`, no HTTP |
| Unit | `aplicar_busqueda`: match by `nombre`, by `codigo`, `?q=auditoria` matches `"Auditoría"`, blank `q` is a no-op | Same |
| Unit | `analizar_definicion_subida`: valid mapping → `(texto, dict)`; non-UTF-8, `!!python/object/apply`, list root, scalar root, non-JSON-representable date → `ValidationError` keyed `archivo_yaml` | `SimpleUploadedFile`, no DB — the RED tests for the extraction |
| Unit | `TipoDeReporteForm`: `plantilla.disabled` True with an active definición / False without; a POSTed `plantilla` on an active tipo does not persist | `test_formularios.py` |
| Unit | `DefinicionDeTipoForm`: valid YAML → `borrador` with derived `yaml_fuente`/`estructura`; `estado`/`version`/`activada_en` absent from `form.fields` | Same |
| Unit | Empty `logo` → `_intercambiar_logo` leaves `hoja._images` untouched | `test_generador.py`, `plantilla_xlsx(imagen=…)` |
| Integration | Auth matrix on all 8 routes: admin 200/302, non-admin 403 **and** no tipo `codigo` in the body, anonymous 302 | Django test client |
| Integration | Pagination/search: 21 tipos → page 1 holds 20, `?page=2` holds 1, `?page=abc`/`?page=999` → 200, `?page=2&q=x` keeps the query string |  |
| Integration | Detail shows active + historical definiciones |  |
| Integration | Activate success → `activa` + success message; multi-problem failure → still `borrador` + one message per problem |  |
| Integration | Desactivate → `definicion_activa is None`, former active `historica`, `version` unchanged |  |
| Integration | Edit tipo with no new `logo` file → `logo.name` unchanged after save (the spec's headline scenario) |  |
| Integration | Oversized `plantilla` (> `reportes.adjuntos.TAMANO_MAXIMO_BYTES`) is accepted (D8) |  |
| Integration | `TipoDeReporte`/`DefinicionDeTipo` absent from `admin.site._registry`; existing `test_admin.py` still green | PR2 |
| Integration | No delete action: no `method="post"` delete form/route exists for either model |  |

Strict TDD (`openspec/config.yaml: rules.tasks`): every row above is a RED
test before its implementation.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Routing | **Applicable** — 8 new routes, 4 of them state-changing | `solo_administradores` on all 8; `@require_POST` + CSRF on the 4 mutating ones; no `?next=`/user-supplied redirect target anywhere (all `redirect()` calls name a route) | Auth matrix ×8; GET on an activate/desactivate route → 405 |
| Untrusted deserialization | **Applicable** — admin-uploaded YAML | Single entry point preserved: `analizar_definicion_subida` → `analizar_yaml_seguro` → `yaml.safe_load`; the new form never calls `yaml.load` and never reimplements the parse | `!!python/object/apply` rejected via the new form *and* via the helper directly |
| Untrusted file parsing | **Applicable** — `.xlsx` reaches openpyxl on activation, images reach Pillow on upload | Unchanged: `activar_definicion` already converts any template read failure into a `plantilla-ilegible` problem; `ImageField` rejects a non-image `logo` | Activation with an unreadable `plantilla` → problem, not 500 |
| Executable-file classification | **Applicable** — stored blobs are served by URL | Unchanged, pre-existing: `VercelBlobStorage` returns a public-but-unguessable URL, exactly as `plantilla`/`logo` do today. No new exposure; proxying downloads stays out of scope | None new |
| Shell / subprocess | N/A — none introduced | | |
| VCS/PR automation | N/A — none introduced | | |
| Process integration | N/A — none introduced | | |

## Migration / Rollout

No migration required — no model field changes. PR1 is purely additive
(delete views/urls/templates/`listado.py`/decorator to roll back; Django
admin remains fully available). PR2's only non-additive edit is the two
`@admin.register(...)` lines, whose rollback is re-adding them (D7). The
`validacion.py` extraction is behaviour-preserving and stays valid either
way. Blob orphaning on re-upload is untouched and remains a documented
`VercelBlobStorage.exists()` limitation.

## Open Questions

- [x] **PR boundary for the decorator.** Resolved by user decision
      (2026-08-30): `usuarios/decorators.py` ships in **PR1**, not PR2, so
      all four of PR1's views are spec-compliant from the start with the
      single gating mechanism — no temporary inline guard.
- [ ] **Navigation entry point.** No screen currently links to
      `tipos_lista`; an administrator must type the URL. A nav link belongs
      in a shared `base.html` header, which backlog #12's design already
      deferred as a follow-up. Confirm the deferral.
- [ ] **`DefinicionDeTipo` edit scope (D5).** Restricting edit to `borrador`
      rows follows from `models.py`'s `CONGELADOS` guard, but the spec says
      only "create and edit forms". Confirm the 404-for-non-borrador read.
