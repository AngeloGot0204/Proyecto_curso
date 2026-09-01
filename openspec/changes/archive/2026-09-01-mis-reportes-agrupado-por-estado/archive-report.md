# Archive Report: mis-reportes-agrupado-por-estado

**Change**: mis-reportes-agrupado-por-estado
**Archived to**: `openspec/changes/archive/2026-09-01-mis-reportes-agrupado-por-estado/`
**Archive Date**: 2026-09-01
**Mode**: openspec

## Resumen

Reemplaza el agrupamiento de "Mis reportes" por relación creador/participante
con tres buckets de estado calculados en lectura, y agrega el filtro
`?relacion=`, el % de avance por tarjeta, el chip de número de registro o
`local`, y el punto de entrada fijo a la pantalla de selección de tipo (S-03).

## Gate de tareas — PASS

24 tareas completas, verificadas contra el disco antes de archivar.

## Specs sincronizadas

| Capacidad | Acción | Destino |
|---|---|---|
| `listado-reportes` | Delta aplicada | `openspec/specs/listado-reportes/spec.md` |
| `seleccion-tipo-reporte` | Creada | `openspec/specs/seleccion-tipo-reporte/spec.md` |

La delta de `listado-reportes` agregó 4 requirements (filtro
creador/compartido/todos, % de avance, chip de número o `local`, CTA fijo),
modificó 2 (agrupamiento por bucket, filtro de estado) y removió 3, que
quedaron superados por los anteriores.

`seleccion-tipo-reporte` se promovió como capacidad nueva. Al aplicarla se le
agregó el requirement "Form Supplies id_local For Idempotent Creation", que
cubre el arreglo del doble click hecho el mismo día: el contrato de
idempotencia del servidor existía pero era inalcanzable desde la interfaz
porque el formulario no mandaba `id_local`.

## Verificación

**Veredicto**: PASS WITH WARNINGS (`verify-report.md`)

- 12/12 requirements, 17/17 scenarios
- 0 blockers, 0 CRITICAL
- Suite enfocada: 58 passed, 0 failed, exit 0
- Redes de seguridad adicionales: `test_generador.py` (31 passed) para probar
  que la extracción de `claves_obligatorias` de D1 no rompió
  `_validar_completitud`, y `test_validacion.py` (6 passed) para la
  dependencia de `validar_reporte`/`puede_generar` de D3

## Estado del bucket calculado

Los tres buckets (`en_progreso`, `listo_para_generar`, `terminado`) se
calculan en cada lectura desde `ValorDeReporte`, `VistoBueno` y
`DefinicionDeTipo`. No introdujeron campo persistido ni migración, y el bucket
es el mismo para todos los que acceden a un reporte: no depende de quién
mira.

La pantalla de Inicio (S-00) reusa exactamente ese mismo pipeline para sus
conteos, de modo que sus números no pueden desincronizarse del listado.

## Ciclo SDD

Planificado, especificado, implementado, verificado y archivado.
