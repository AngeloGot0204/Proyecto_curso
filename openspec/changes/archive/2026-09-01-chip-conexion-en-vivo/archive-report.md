# Cierre: Live Connection Chip in Screen Bar

**Estado: cerrado y archivado — 2026-09-01.**

## Qué se entregó

| Pieza | Archivo |
|---|---|
| Script del chip | `static/js/conexion-chip.js` (IIFE, lectura síncrona en load, listeners `online`/`offline`) |
| Partial compartido | `templates/_chip_conexion.html` |
| Carga global | `templates/base.html` (`defer`) |
| Estilo | `static/css/components.css` (`.barra-pantalla__conexion`) |

## Cobertura completada al cerrar

La spec exige el chip en **toda** pantalla que renderice `.barra-pantalla`.
El change original lo había incluido solo en 3 templates (`paso`,
`mis_reportes`, `adjuntos`), dejando 9 pantallas sin él y el contrato sin
cumplir.

Al cerrar se incluyó el partial en las 9 restantes:

- `reportes/revision.html`
- `reportes/seleccion_tipo.html`
- `tipos_reporte/detalle.html`
- `tipos_reporte/formulario_definicion.html`
- `tipos_reporte/formulario_tipo.html`
- `tipos_reporte/lista.html`
- `usuarios/formulario_usuario.html`
- `usuarios/lista.html`
- `usuarios/resetear_password.html`

Cobertura final: **16 de 16** pantallas con barra. El login sigue sin chip,
como exige la spec, porque no renderiza `.barra-pantalla`.

La spec pasó a `openspec/specs/capa-offline/spec.md` como el requirement
"Live Connection Chip in Shared Screen Bar", con un escenario agregado que fija
la cobertura total ("Chip appears on every screen with a bar").

## Verificación manual pendiente — NO cerrada

Dos chequeos requieren un navegador real con throttling de red en DevTools y
**quedan sin verificar**:

| Task | Qué falta comprobar |
|---|---|
| 5.1 | Con red online, el chip muestra "en línea" inmediatamente al cargar, sin flash de estado incorrecto |
| 5.2 | Con el throttle "Offline" de DevTools, el chip pasa a "offline" en vivo sin recargar, vuelve al reconectar, y el banner de borrador de `paso-offline.js` no se ve afectado |

La ausencia del chip en login (5.3) sí quedó cubierta por
`test_chip_conexion_ausente_en_login`, porque es un chequeo de presencia
estática y no de evento de red.
