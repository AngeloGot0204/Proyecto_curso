# ADR 0003: Tipos de reporte definidos por configuración declarativa y valores en almacenamiento genérico

## Estado

Aceptado

## Contexto

El PRD establece como criterio de éxito verificable que "agregar un segundo tipo de reporte
(basado en una plantilla ya definida) no requiere cambios en el código de la lógica de generación
de reportes ya existente, solo la nueva configuración", y sitúa dentro del alcance un "diseño de
datos basado en plantillas/configuración por tipo de reporte (no hardcodeado a un único Excel)".

Esta exigencia no es especulativa: el propio archivo de referencia contiene, en hojas ocultas, un
**segundo formato de reporte distinto** (Plan de Puntos de Inspección y Ensayos para concreto
lanzado / Shotcrete), con su propia estructura de columnas. El segundo tipo de reporte ya existe
en la operación.

Además, la ADR-0002 dejó pendiente un artefacto que debe vivir en algún lugar: el **mapeo campo →
celda** que la generación del `.xlsx` necesita para saber dónde escribir cada valor.

El DESIGN refuerza la necesidad de una estructura declarativa: las pantallas S-05 a S-08 muestran
checklists organizados en secciones, con columnas por rol donde **sólo la columna del rol activo
es editable**, y S-14 presenta el tipo de reporte como una tabla de solo lectura de secciones
(nombre · ítems · roles) que el administrador activa o desactiva.

## Decisión

Definir cada tipo de reporte mediante un **archivo de configuración declarativo** que describe sus
secciones, sus campos e ítems, el tipo de dato de cada uno, el rol responsable de completarlo y la
celda de destino en la plantilla `.xlsx`. La aplicación **lee esa definición** para renderizar el
formulario del wizard y para recorrerla al generar el Excel.

Los valores capturados se guardan en un **almacenamiento genérico** (una fila por valor,
identificada por reporte, identificador de campo, autor y fecha) en lugar de una columna por campo.

**Aclaración (decisión #2 de RESOLUCION-ADVERSARIAL.md):** este almacenamiento **no** lleva un
campo de rol de usuario, y esto no es una omisión. No hay roles de usuario ni permisos por
sección: cualquier persona con acceso al reporte puede editar cualquier campo, como una hoja de
cálculo compartida (ADR-0006). El modelo guarda **un valor por celda**, que se pisa con la última
edición; el `rol` que aparece en la definición declarativa de más abajo (`roles:
[construccion-jme, qa-subterra]`) identifica la columna del checklist del documento Excel, no un
permiso de edición.

Incorporar un nuevo tipo de reporte consiste en subir su plantilla `.xlsx` y escribir su archivo de
configuración; no requiere modificar la lógica de renderizado ni la de generación.

Ejemplo ilustrativo de la forma de la definición:

```yaml
tipo: instalacion-resinas
plantilla: JME.PC-0001.F1.xlsx
secciones:
  - id: datos-generales
    titulo: Datos generales
    campos:
      - id: turno
        etiqueta: Turno
        tipo: seleccion
        opciones: [Día, Noche]
        obligatorio: true
        celda: M12
  - id: proceso-instalacion
    titulo: Proceso de instalación
    roles: [construccion-jme, qa-subterra]
    items:
      - id: p-01
        texto: Se verifica ángulo de perforación.
        tipo: hora-inicio-fin
        celda_inicio: M25
        celda_fin: P25
```

## Alternativas consideradas

- **Un modelo Django dedicado por tipo de reporte, con columnas reales** (`turno`, `tipo_roca`,
  `item_01_jme`, …) — era plenamente viable y bastante más simple de construir: aporta tipado
  fuerte, validación automática mediante formularios de Django, consultas directas y errores
  detectados temprano. Se descartó porque **incumple el criterio de éxito del PRD**: cada tipo de
  reporte nuevo exigiría tablas, migraciones y formularios nuevos, es decir código y no
  configuración. Se consideró además que migrar más adelante de columnas fijas a un esquema
  genérico no sería una ampliación sino una reescritura del modelo de datos, de los formularios y
  de los datos ya cargados en producción.

- **Un `JSONField` por reporte, guardando todos sus valores en un único documento JSON** (decisión
  #7 de RESOLUCION-ADVERSARIAL.md) — se evaluó como alternativa intermedia entre columnas fijas y
  la tabla genérica: menos tablas, escritura de un reporte completo en una sola fila. Se descartó
  porque la autoría y fecha **por campo** — necesaria para el historial de cambios de la edición
  abierta (ADR-0006) — no se obtiene gratis con un JSON: habría que anidar autor/fecha dentro de
  cada clave del documento a mano. Con el modelo de una fila por valor, autor y fecha ya son
  columnas de la fila y vienen resueltos por diseño.

- **Definición de tipos de reporte editable desde la interfaz de administración (self-service)** —
  habría permitido al administrador crear tipos de reporte sin intervención técnica. Se descartó
  porque el PRD lo excluye explícitamente en "No alcance" ("la definición de la plantilla es
  configuración, no self-service en el MVP") y porque exige construir un editor visual de
  formularios, desproporcionado para el MVP.

## Consecuencias

- Se cumple el criterio de éxito del PRD sobre extensibilidad de forma verificable: el segundo
  tipo de reporte (PPI Shotcrete) se incorpora como configuración.
- El mapeo campo → celda pendiente de la ADR-0002 queda resuelto y centralizado en un único
  artefacto, junto al resto de la definición del reporte.
- La regla del DESIGN de "sólo la columna del rol activo es editable" se expresa de forma
  declarativa (el rol responsable se declara por sección o ítem), en lugar de repartirse por el
  código de las plantillas.
- La pantalla S-14 puede listar secciones, ítems y roles leyendo directamente la definición, sin
  lógica específica por tipo de reporte.
- **Costo real:** se pierde el tipado fuerte y la validación automática que Django ofrece sobre
  modelos con columnas concretas; las reglas de validación deben interpretarse en tiempo de
  ejecución a partir de la configuración.
- **Costo real:** las consultas analíticas se vuelven más incómodas — obtener "todos los reportes
  con turno noche" deja de ser un filtro directo y pasa por un join sobre la tabla genérica de
  valores. El PRD excluye analítica del alcance, por lo que este costo es aceptable hoy, pero
  reaparecerá si más adelante se incorporan reportes de gestión.
- **Costo real:** un error en un archivo de configuración no lo detecta el compilador y se
  manifiesta en tiempo de ejecución. Es necesario **validar la definición al cargarla** (campos
  obligatorios presentes, tipos conocidos, celdas con formato válido y sin colisiones) para que
  el fallo se produzca al publicar el tipo de reporte y no frente al usuario en campo.
- **Costo real:** la indirección añade dificultad de depuración — al investigar un dato incorrecto
  hay que revisar tres lugares (la definición, el valor almacenado y la plantilla) en vez de uno.
