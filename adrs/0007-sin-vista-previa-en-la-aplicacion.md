# ADR 0007: Sin vista previa del reporte dentro de la aplicación

## Estado

Aceptado

## Contexto

El PRD incluía en el alcance una "pantalla de revisión del reporte generado antes de descargarlo
(para detectar errores antes de entregarlo)", y el DESIGN la desarrollaba en dos pantallas: S-11
(revisión previa en móvil, con paginado y zoom) y S-12 (revisión previa en escritorio, con
previsualización a la izquierda y panel de chequeo por sección a la derecha). El DESIGN dejaba
además una decisión abierta en su sección 10: "si la vista previa se genera del lado servidor
(fiel al Excel) o es una aproximación HTML".

Se evaluaron tres niveles de fidelidad, de mayor a menor costo:

1. **Vista previa fiel del `.xlsx` real**, convirtiendo el documento a imagen o PDF para mostrarlo
   en el navegador. Requiere LibreOffice u equivalente en el servidor, precisamente la dependencia
   pesada descartada en la ADR-0002.
2. **Maqueta HTML que imita el documento** (encabezado, checklists, bloque de firmas). No requiere
   dependencias nuevas, pero implica replicar la maquetación del reporte en HTML.
3. **Lista de repaso**: los datos agrupados por sección, sin imitar el documento.

Al presentarle estas opciones, el usuario resolvió **eliminar la vista previa por completo**,
priorizando la simplicidad del MVP.

## Decisión

**No incluir vista previa del reporte dentro de la aplicación.** Se eliminan las pantallas S-11 y
S-12. Tras el visto bueno (ADR-0006), el usuario descarga directamente el `.xlsx` generado y lo
revisa en Excel.

La función de revisión previa a la emisión queda cubierta por dos mecanismos ya existentes:

- **S-09 (validación al cerrar)**, que enumera los errores que bloquean y las advertencias que no,
  con enlace al campo exacto.
- **La navegación libre del wizard** entre pasos ya visitados, que permite al usuario repasar y
  corregir sus datos antes de cerrar.

## Alternativas consideradas

- **Vista previa fiel del `.xlsx` convertido a imagen o PDF** — era la opción más completa y la que
  el DESIGN describía como "vista previa fiel". Se descartó por coherencia con la ADR-0002: exige
  instalar y mantener LibreOffice en el servidor, con procesos lentos, consumo de memoria alto y
  fragilidad de despliegue, desproporcionado para un proyecto mantenido por una sola persona.

- **Maqueta HTML que imita el documento** — no añade dependencias y ofrece una revisión visual
  cercana al resultado. Se descartó porque obliga a replicar en HTML el encabezado institucional,
  los checklists y el bloque de firmas, es decir mantener una segunda representación del reporte
  en paralelo a la plantilla `.xlsx`, con el riesgo de que ambas diverjan.

- **Lista de repaso de los datos agrupados por sección** — fue la opción recomendada por ser
  notablemente más barata que la maqueta y cumplir el propósito real de la revisión (verificar los
  datos, no el formato, que la plantilla ya garantiza). **El usuario la descartó** en favor de
  eliminar la vista previa por completo y simplificar aún más el MVP.

## Consecuencias

- Se eliminan dos pantallas del alcance (S-11 y S-12), una de ellas de escritorio, reduciendo de
  forma apreciable el trabajo de construcción del MVP.
- No hay una segunda representación del reporte que mantener sincronizada con la plantilla.
- Se evita por completo la dependencia de LibreOffice en el servidor.
- **Costo real:** el usuario sólo ve el resultado final al abrir el archivo descargado. Si el
  mapeo campo → celda de la ADR-0002 tiene un error, no se detecta dentro de la aplicación.
- **Costo real, mitigación obligatoria:** la verificación campo a campo contra el documento de
  referencia al configurar cada tipo de reporte deja de ser una buena práctica y pasa a ser el
  único control manual de corrección del mapeo. Ya figura como criterio de éxito en el PRD y debe
  ejecutarse una vez por cada tipo de reporte antes de activarlo.
- **Mitigación adicional (decisión #15 de RESOLUCION-ADVERSARIAL.md): prueba automática de
  "archivo dorado".** La revisión manual celda a celda no se repite sola en cada cambio de código;
  se suma una prueba automatizada que genera un reporte con datos fijos y compara el `.xlsx`
  resultante contra un archivo `.xlsx` esperado, versionado en el repositorio. Corre en cada
  cambio al generador o al mapeo, sin depender de que alguien repita la revisión manual a mano.
- **Costo real:** revisar el documento en campo desde un celular exige abrir un `.xlsx`, algo
  incómodo en pantalla pequeña. El usuario asumió esta molestia de forma consciente al eliminar
  la vista previa.
- **Costo real:** el PRD ya excluye la edición de un reporte una vez generado, de modo que un
  error detectado tras la descarga obliga a rehacer el reporte o a corregir el archivo fuera de
  la aplicación.
