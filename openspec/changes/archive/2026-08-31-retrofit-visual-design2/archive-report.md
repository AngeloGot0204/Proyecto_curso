# Archive Report: retrofit-visual-design2

**Change**: retrofit-visual-design2 (backlog #15)
**Archived to**: `openspec/changes/archive/2026-08-31-retrofit-visual-design2/`
**Archive Date**: 2026-09-01
**Mode**: openspec

## Nota sobre este reporte — la fase Verify nunca corrió

Este es el único cambio del proyecto archivado **sin fase Verify**: la carpeta
no tiene `verify-report.md` y nunca se produjo uno. No se puede reconstruir
retroactivamente, porque un verify afirma que alguien comprobó algo en un
momento dado, y eso no ocurrió.

Lo que este reporte hace en su lugar es declarar esa ausencia y registrar la
evidencia que **sí** existe hoy, obtenida el 2026-09-01, distinguiendo con
claridad una cosa de la otra.

`apply-progress.md` agrega una segunda señal de que el ciclo quedó a medias:
su último estado dice "17/17 Phase 1 tasks complete. Phases 2–4 untouched.
Ready for verify on Phase 1 / PR1a". Las fases 2 a 4 se completaron después
—`tasks.md` tiene sus 60 tareas marcadas— pero ni `apply-progress` ni ningún
verify registraron ese tramo.

## Resumen

Aplicación del lenguaje visual DESIGN2 a los templates: `tokens.css` y
`components.css` enlazados una sola vez desde `base.html`, tipografía mono
self-hosted, y extensión del cache del service worker para cubrir los nuevos
estáticos. Sin cambio de comportamiento.

## Gate de tareas

60 tareas marcadas completas en `tasks.md`, 0 sin marcar. A diferencia de los
otros cambios del proyecto, **estas marcas no fueron auditadas por un verify**:
se las registra como están, sin avalarlas.

## Specs sincronizadas

| Capacidad | Acción | Destino |
|---|---|---|
| `visual-design-system` | Creada, 5 requirements | `openspec/specs/visual-design-system/spec.md` |
| `capa-offline` | Extendida, 1 requirement | `openspec/specs/capa-offline/spec.md` |

Ambas viven hoy en `openspec/specs/`. `visual-design-system` fue extendida
después con los requirements del sidebar y de los toasts.

## Evidencia verificada el 2026-09-01

Comprobado directamente contra el código en la sesión de auditoría, no
heredado de ninguna afirmación previa:

| Qué | Resultado |
|---|---|
| `base.html` enlaza `tokens.css` y `components.css` | Confirmado, una sola vez, sin CDN de terceros |
| Fuente mono self-hosted | `static/fonts/IBMPlexMono-{Regular,Medium}.woff2` presentes, con su licencia OFL |
| Sin framework ni build step | Confirmado: no hay `package.json` ni paso de compilación |
| Suite estáticos + `tipos_reporte` + `usuarios` | 212 passed |
| Suite del repositorio excluyendo `test_views.py` | 366 passed |
| `test_views.py` | 112 passed |

## Lo que sigue sin verificarse

La afirmación central del cambio —**"zero behavior change"**— no fue
comprobada por un verify en su momento y no es comprobable ahora de forma
retroactiva: haría falta comparar el comportamiento contra el estado previo al
retrofit, y ese estado ya no existe en el árbol de trabajo.

Lo que sí sostiene esa afirmación hoy es que la suite completa pasa y que
ningún test de comportamiento cambió junto con el retrofit. Es evidencia
indirecta, no una verificación.

## Ciclo SDD

Planificado, especificado, implementado y archivado. **Sin fase Verify** — el
único cambio del proyecto en esa condición, registrado aquí para que no se
lea como un ciclo completo.
