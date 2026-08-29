# Exploration: Colaboración por invitación y edición abierta (Backlog #8)

## Current State

**ADR-0006 is the authoritative source.** Key decisions:
- **Invitation-only access**: creator explicitly grants access to specific users; no role-derived automatic access. Only creator + invited users can see/work the report.
- **Open editing**: any participant with access can edit any section/column, including other roles' columns — deliberately chosen over role-restricted editing.
- **`CambioDeValor` audit is the mandatory counterpart** to open editing — every write records author, field, previous value, timestamp. This is what makes open editing acceptable; traceability moves from access control to history.
- **Manual closing stays creator-only** (`reporte.creado_por == usuario_actual`) — `ParticipacionEnReporte` deliberately carries **no** "responsible for closing" field; already implemented in #7, does NOT change in #8.
- **Online-only edit lock** ("en edición por `<usuario>`", read-only for others, released manually or after 10 min inactivity) — described in ADR-0006 but NOT listed in BACKLOG.md item #8's scope text. Treat as likely-deferred/separate mechanism — flag as open decision.
- Two "costo real" items explicitly flagged unresolved: (a) a report can stay complete-but-unclosed forever with no admin override; (b) a report whose creator forgets to invite anyone is inaccessible to others. Neither is #8's job, but both point at future admin-override work.

**TECH-DESIGN.md model table gives exact shapes**:
- `ParticipacionEnReporte`: "qué usuario tiene acceso a qué reporte" — invitation record, no responsibility/role field.
- `CambioDeValor`: "quién editó qué campo, valor anterior y cuándo." **Retention is explicit**: cola FIFO de los últimos 30 cambios **por reporte completo (no por campo individual)**; al registrarse el cambio 31 de un reporte, se elimina el más antiguo de ese mismo reporte. FIFO-30 is scoped **per `Reporte`**, not per field.

**Acceptance criteria**:
- Creator can invite another user; that user then sees the report in their listing.
- A non-invited user cannot access the report, ni por enlace directo (direct-URL access must also be blocked — every reporte-scoped view needs the access check).
- An invited user can edit any section; each edit is recorded with author, field, previous value, date, viewable from S-10.
- (Visto bueno / generation ACs already satisfied by #7.)

**DESIGN.md**: S-10 is the "participants + visto bueno" screen — list of invited participants, "Compartir con…" invite action, section progress, change history access, existing creator-only "Marcar como terminado" (already built in #7). S-10 does NOT exist as a template yet — only `revision.html` (S-09) exists, with no participants list, no invite action, no `CambioDeValor` view.

DESIGN.md explicitly flags an **open pending decision**: the notification mechanism when inviting ("correo, notificación o sólo en la lista") is unresolved. No email backend exists anywhere in the repo (confirmed: zero `EMAIL_BACKEND`/`EMAIL_HOST`/`django.core.mail` hits) — "solo en la lista" (in-app listing only) is the only option requiring zero new infrastructure.

## Current access-control state (`reportes/views.py`)

- `paso` and `revision`: both `get_object_or_404(Reporte, pk=reporte_id, creador=request.user)` — strictly creator-only. **Must change** to "creator OR invited participant."
- `cerrar_reporte`: same creator-only lookup — **must stay creator-only** per ADR-0006, unchanged.
- `generar`: NOT creator-scoped today — `get_object_or_404(Reporte, pk=reporte_id)` with no filter, any authenticated user (deliberate #7 decision, explicitly deferred to #8's decision per #7's own exploration.md: "Recommend: any authenticated user, deferred fine-grained access to #8"). **Open question for #8**: stay open, or narrow to creator-or-participant now that `ParticipacionEnReporte` exists? ADR-0006's premise is "only the creator and invited users see and work the report" — an arbitrary authenticated user downloading a closed report's document contradicts that. Recommend narrowing.
- `iniciar_reporte`: creates the report; creator automatically has access — recommend "is creator" always-allowed independent of `ParticipacionEnReporte` rows (mirrors how `cerrar_reporte`'s check stays creator-based without a participation row).

## `guardar_valor` write path (`reportes/valores.py`)

- `guardar_valor(reporte, identificador_de_campo, valor, autor)` is the single upsert/delete point for `ValorDeReporte`, called only from `views.py::paso`'s POST branch — the correct and only place to also write `CambioDeValor`.
- Current logic: empty value deletes; non-empty upserts. `CambioDeValor` needs "valor anterior" fetched **before** the write (no read-before-write exists today — new code path).
- FIFO-30 trim (delete oldest `CambioDeValor` row for that `reporte` once the 31st is inserted) needs to happen atomically alongside the insert — `transaction.atomic()`, similar to `cerrar_reporte`'s existing pattern. Django forbids `.delete()` directly on a sliced queryset — needs a `pk__in` subquery pattern.
- Every `guardar_valor` call already knows the acting user (`request.user`, passed as `autor`) — no extra plumbing needed.

## `usuarios/models.py`

- `Usuario(AbstractUser)`: `username` unique; `email` blank=True, NOT unique/required. **Invitation lookup must be by username**, not email. No search/lookup view exists in `usuarios/views.py`.
- No email-sending infrastructure anywhere — confirms "solo en la lista" is the zero-new-infra invitation UX.

## Is "open editing" already effectively true today?

**No.** Today only the creator can edit at all (`paso` is creator-scoped); there's no invitation mechanism, so "open editing among participants" doesn't exist — only "creator editing," a degenerate 1-participant case. #8 must both (a) build `ParticipacionEnReporte` + invite UX, and (b) widen the access check. Nothing about column/section-level restriction exists to remove — `construir_formulario_seccion` builds one form per section with no role filtering already, so "edición abierta" is already the shape of the wizard; #8's job is purely who gets to reach it.

## Test Conventions

Established pattern for creator-only 404s: `test_paso_reporte_de_otro_usuario_da_404`, `test_get_revision_reporte_de_otro_usuario_da_404`, `test_cerrar_reporte_no_creador_devuelve_404` — all follow: create `otro_creador`, `reporte = reporte_factory(creador=otro_creador)`, hit as a different authenticated user, assert 404. #8 needs the inverse: an invited-but-not-creator user gets 200; a non-invited user still gets 404.

## Affected Areas
- `reportes/models.py` — add `ParticipacionEnReporte` (reporte FK, usuario FK, likely `fecha_invitacion`, unique-together reporte+usuario) and `CambioDeValor` (reporte FK, identificador_de_campo, valor_anterior, autor FK, fecha).
- `reportes/valores.py::guardar_valor` — read-before-write for `valor_anterior`, write `CambioDeValor`, FIFO-30 trim, inside `transaction.atomic()`.
- `reportes/views.py` — widen `paso`/`revision` access checks; decide `generar`'s scope; add invite view + S-10-equivalent view.
- `reportes/urls.py` — new routes.
- New template (S-10 doesn't exist yet).
- `reportes/migrations/` — new `0004_...`.
- Tests: models, valores (CambioDeValor + FIFO trim), views (participant-access, invite).

## Approaches

1. **Minimal invite-list model** — `ParticipacionEnReporte` plain join table (reporte, usuario, fecha), invite by exact username, widen access checks, `CambioDeValor` write in `guardar_valor`, "solo en la lista" notification (no email).
   - Pros: matches ADR-0006 literally; zero new infra; smallest slice satisfying all ACs.
   - Cons: user must know exact username (no search) — acceptable, no AC requires search.
   - Effort: Low.

2. **Same as 1 + username/email search-as-you-type.**
   - Pros: nicer UX.
   - Cons: no AC requires it; premature given zero user-search infra.
   - Effort: Medium.

3. **Defer `CambioDeValor`/FIFO-30, ship only invitation + access restriction.**
   - Cons: directly contradicts ADR-0006 ("contrapartida obligatoria") and BACKLOG.md's own bundled text — not a legitimate split.

## Recommendation

**Approach 1.** Literal minimal reading of ADR-0006/TECH-DESIGN, zero new infra, mirrors the codebase's established "smallest AC-satisfying slice" pattern. Invite by exact username (not email — unset/non-unique). `generar`'s scope is the one real open decision — recommend narrowing to creator-or-participant, but must be an explicit proposal decision, not silent.

## Open Decisions (must be settled in proposal)
1. Does `generar` stay open to any authenticated user, or narrow to creator-or-participant?
2. Is the online simultaneous-edit lock ("en edición por...", 10-min timeout) in scope for #8, or deferred? BACKLOG.md's #8 text doesn't mention it; ADR-0006 documents it under the same section.
3. Exact `ParticipacionEnReporte` field shape — `fecha_invitacion`/`invitado_por`, or just `(reporte, usuario)`?
4. Should the creator's own edits also get a `ParticipacionEnReporte` row (for symmetry in S-10's participant list), or does S-10 special-case "creator + invited list" separately?

## Risks
- FIFO-30 trim-on-31st-write is a non-trivial query (Django forbids `.delete()` on a sliced queryset) on a write-heavy path (every wizard step upserts multiple fields) — needs performance-aware implementation and boundary test coverage (30th vs 31st write).
- `guardar_valor` currently has no read-before-write; adding one changes its transaction shape — recommend one `transaction.atomic()` wrapping the value write + audit insert + trim.
- `generar`'s access scope is unresolved from #7 and must not be silently decided during apply.
- Notification-mechanism-out-of-scope assumption (no email) needs explicit confirmation.
- No S-10 template exists yet — new UI surface, not wiring an existing dead button (unlike #7's `revision.html`).
- Online edit-lock, if pulled into scope, adds a meaningfully larger stateful "locked by X since Y" mechanism than the rest of #8.

## Key Learnings
1. ADR-0006 mandates invitation-only access with fully open editing among participants, backed by a mandatory per-Reporte FIFO-30 `CambioDeValor` audit trail (not per-field).
2. Today's model (creator-only edit) is stricter than ADR-0006's target, not a degenerate case of it — #8 must both build the invite mechanism and widen access checks.
3. `generar`'s "any authenticated user" access was explicitly deferred from #7 to #8 for reconsideration.
4. No email infrastructure exists anywhere in the repo — "solo en la lista" is the zero-infra invitation notification default.
5. Django forbids `.delete()` on a sliced queryset, so FIFO-30 trim needs a `pk__in` subquery pattern.

**Next**: sdd-propose (pending resolution of the 4 open decisions above)
