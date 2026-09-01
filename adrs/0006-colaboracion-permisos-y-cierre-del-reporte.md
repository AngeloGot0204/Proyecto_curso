# ADR 0006: Colaboración por invitación explícita, edición abierta con registro de cambios y cierre manual

## Estado

Aceptado

## Contexto

El PRD establece que varios usuarios participan en un mismo reporte y que el documento sólo puede
generarse cuando todas las partes requeridas están completas. El DESIGN traduce esto en la
pantalla S-10 (handoff entre roles) y en la regla de S-05 según la cual "sólo la columna del rol
activo es editable".

El reporte de referencia refuerza esa lógica documental: incluye columnas de verificación separadas
por rol (Consorcio JME / QA Subterra / QC JME / QA Antamina) y cuatro bloques de firma
independientes, de modo que la separación por rol constituye la trazabilidad del documento.

Durante la entrevista de diseño técnico, el usuario definió un modelo de colaboración distinto del
supuesto en el PRD y el DESIGN:

1. Quien crea el reporte puede **compartirlo explícitamente** con otro usuario, otorgándole
   permiso para trabajar en él.
2. El usuario invitado puede **trabajar y editar el reporte donde sea necesario**, sin quedar
   restringido a la columna de su rol.
3. El reporte se da por terminado cuando **la persona encargada de revisarlo da el visto bueno** y
   lo marca como terminado, en lugar de deducirse automáticamente de que todas las secciones estén
   completas.

Se planteó al usuario el riesgo de la edición abierta: si cualquier participante puede completar
cualquier columna, el documento podría afirmar que un rol verificó algo que no verificó, lo cual
erosiona precisamente el valor que control de calidad audita. Se le presentó la alternativa
restrictiva (cada rol edita sólo su columna) y **el usuario optó deliberadamente por la edición
abierta**, priorizando la flexibilidad operativa: poder corregir errores y avanzar cuando alguien
del equipo no está disponible.

## Decisión

**Acceso por invitación explícita.** El creador del reporte otorga permiso a usuarios concretos.
Sólo el creador y los usuarios invitados ven y trabajan el reporte; no hay acceso automático
derivado del rol.

**Edición abierta dentro del reporte compartido.** Cualquier participante con permiso puede editar
cualquier sección o columna del reporte, incluidas las de otros roles.

**Registro de cambios (auditoría) como contrapartida obligatoria.** Toda escritura queda registrada
con el usuario que la realizó, el campo afectado, el valor anterior y la marca de tiempo. Este
registro es la mitigación que hace aceptable la edición abierta: la trazabilidad se traslada del
control de acceso al historial.

**Cierre manual del reporte.** El estado terminado no se deduce: un usuario responsable revisa el
reporte y lo marca explícitamente como terminado (visto bueno). Ese acto habilita la generación
del `.xlsx` y queda registrado con autor y fecha.

**Quién puede cerrar (decisión #11 de RESOLUCION-ADVERSARIAL.md).** El botón "Marcar como
terminado" de S-10 se habilita únicamente si el usuario actual es el **creador** del reporte
(`reporte.creado_por == usuario_actual`). No se agrega un campo nuevo de responsabilidad en
`ParticipacionEnReporte`: la comprobación es directa contra el creador ya existente en `Reporte`.
Por ahora **no hay intervención de administrador** si el creador nunca da el visto bueno y el
reporte queda completo sin cerrar — queda pendiente para una versión posterior.

**Bloqueo de edición para uso simultáneo online (decisión #3 de RESOLUCION-ADVERSARIAL.md) —
NO IMPLEMENTADO.** **(Nota 2026-09-01)** Esta ADR había decidido un bloqueo "en edición por
`<usuario>`" con liberación manual o por 10 minutos de inactividad, pero nunca se construyó: no
hay en el código ningún campo, vista ni JS que marque un reporte como "en edición" ni que lo
ponga en solo lectura para otros participantes. Hoy dos participantes pueden editar el mismo campo
a la vez sin aviso; solo queda el registro de cambios (`CambioDeValor`) para reconstruir qué pasó
después. Esta misma decisión está repetida (y también sin construir) en ADR-0004 y ADR-0008 —
si se sigue queriendo, requiere spec y diseño propios antes de implementarse.

## Alternativas consideradas

- **Acceso automático por rol, con cada rol editando sólo su columna** (el modelo supuesto
  originalmente en el PRD y el DESIGN) — preserva de forma estructural la trazabilidad del
  documento, ya que resulta imposible que un participante complete la verificación de otro, y
  refleja con exactitud la separación de responsabilidades del formato oficial. **Fue presentada
  como recomendación y el usuario la descartó explícitamente** en favor de la flexibilidad
  operativa: evitar que un reporte quede bloqueado y permitir corregir errores ajenos sin
  depender de la disponibilidad de cada persona.

- **Cierre automático del reporte al completarse todas las secciones** — elimina un paso manual y
  evita que un reporte terminado quede sin cerrar por olvido. Se descartó porque el usuario
  requiere un punto explícito de revisión y visto bueno antes de considerar el informe terminado;
  completar los campos no equivale a haberlos validado.

- **Edición abierta sin registro de cambios** — habría sido más simple de construir. Se descartó
  porque dejaría al documento sin ninguna forma de responder quién completó cada verificación,
  combinando la ausencia de restricción con la ausencia de rastro.

## Consecuencias

- Modelo de permisos simple y explícito: el acceso se concede, no se infiere. Resulta más fácil de
  entender y de implementar que una matriz de roles por sección.
- Ningún reporte queda bloqueado por la ausencia de una persona: cualquier participante invitado
  puede avanzar el trabajo.
- El punto de visto bueno introduce una revisión humana deliberada antes de emitir el documento
  final. No existe una pantalla de revisión previa dentro de la app (S-11/S-12 fueron eliminadas
  por ADR-0007); la revisión ocurre sobre el `.xlsx` ya generado.
- El registro de cambios aporta un beneficio adicional no previsto: permite reconstruir la
  historia del reporte ante una discrepancia.
- **Costo real:** la trazabilidad deja de estar garantizada por el sistema y pasa a depender del
  registro de cambios. El `.xlsx` generado no distingue quién completó cada columna, de modo que
  el documento entregado no refleja por sí solo esa información: sólo la aplicación la conserva.
  Es una consecuencia aceptada de forma consciente al elegir la edición abierta.
- **Costo real:** el registro de cambios es desarrollo adicional (modelo, escritura en cada
  actualización y una vista para consultarlo) que no existiría bajo el modelo restrictivo.
- **Costo real:** un reporte puede quedar completo pero sin cerrar si el creador nunca da el visto
  bueno (sólo él puede hacerlo, ver decisión sobre "quién puede cerrar" más arriba), y por ahora no
  hay forma de que un administrador intervenga para destrabarlo. La interfaz debe hacer visible ese
  estado para que no se acumulen reportes listos y no emitidos, mientras esa intervención de
  administrador no se construya.
- **Costo real:** al depender el acceso de una invitación explícita, un reporte cuyo creador olvide
  compartirlo queda inaccesible para el resto. Conviene prever que un administrador pueda
  intervenir.

## Impacto sobre documentos previos

Esta decisión **modifica** supuestos ya escritos, que se actualizan en consecuencia:

- **PRD** — la regla "cada uno en la parte/columna de checklist que le corresponde según su rol" y
  el handoff secuencial por rol se sustituyen por el modelo de invitación explícita con edición
  abierta; la generación deja de habilitarse por completitud automática y pasa a habilitarse por
  el visto bueno manual.
- **DESIGN** — la regla de S-05 "sólo la columna del rol activo es editable" deja de aplicarse. La
  pantalla S-10 pasa de ser una tabla de handoff por rol a una vista de participantes invitados,
  avance y visto bueno. Los estados de la sección 7 incorporan el cierre manual.
