# ADR 0002: Generar el .xlsx rellenando la plantilla original con openpyxl

## Estado

Aceptado

## Contexto

El PRD exige que el documento generado replique **de forma exacta** el formato del reporte de
referencia (`REPORTE DE INSTALACION DE RESINAS (1).xlsx`, formato `JME.SGC.18138.PC-0001-F1`), y
registra como riesgo abierto que "replicar el formato Excel de forma exacta (celdas combinadas,
estilos, checklist por rol) desde datos de formulario es más costoso técnicamente que generar un
documento simple; se recomienda validarlo temprano en diseño técnico con un caso real".

La hoja del reporte tiene 64 celdas combinadas, una imagen de logo, área de impresión definida
(`$B$2:$V$65`), escala de impresión al 50% con ajuste a página y márgenes específicos. El
documento se imprime y se firma a mano por cuatro roles, de modo que el diseño de página no es
cosmético: es parte del entregable.

Este riesgo se validó empíricamente antes de decidir. Se abrió el archivo de referencia con
openpyxl y se volvió a guardar, comparando el resultado:

| Elemento de la hoja del reporte | Original | Tras round-trip con openpyxl |
|---|---|---|
| Área de impresión | `$B$2:$V$65` | idéntica |
| Orientación / escala / ajuste a página | vertical, 50%, fitToPage | idénticos |
| Márgenes | idénticos | idénticos |
| Celdas combinadas | 64 | 64 |
| Imagen (logo) | 1 | 1 |

Las pérdidas detectadas quedan **fuera** de la hoja del reporte: una imagen `.wmf` y un dibujo
pertenecientes a hojas ocultas, los archivos `printerSettings*.bin` (configuración del driver de
impresora, no el diseño de página, que sí se conserva en el XML de la hoja) y metadatos
`customXml`. Ninguno de esos elementos forma parte del documento a entregar.

Conclusión de la validación: el riesgo señalado en el PRD queda acotado **siempre que la plantilla
original se use como base en lugar de construir el libro desde cero**.

**Validación empírica adicional, sobre escritura y exportación (decisión #5 de
RESOLUCION-ADVERSARIAL.md).** El round-trip de arriba confirma que el *formato* sobrevive; hacía
falta confirmar además que *escribir* valores y *exportar* el resultado no lo rompen. Se corrió
sobre la plantilla real `REPORTE DE INSTALACION DE RESINAS (1).xlsx`, hoja del reporte (64 rangos
combinados):

| Prueba | Resultado |
|---|---|
| Escritura en la celda ancla (superior-izquierda) de un rango combinado — 20 casos | 20/20 OK |
| Escritura en una celda NO-ancla de un rango combinado | Falla con `AttributeError: 'MergedCell' object attribute 'value' is read-only` — confirma el riesgo previsto |
| Fórmulas en la hoja del reporte | No existen; el riesgo de "fórmula descartada al escribir con openpyxl" **no aplica** a esta plantilla |
| Exportar sólo la hoja del reporte + guardar | Funciona, el archivo resultante no queda corrupto |
| Logo (imagen PNG) tras guardar | Sobrevive, se conserva en el archivo exportado |

Esto confirma la premisa completa de esta ADR: escribir es seguro siempre que la celda destino sea
la ancla de su rango combinado, y exportar sólo la hoja del reporte no daña el archivo. La regla de
"celda destino = ancla del rango combinado" se agrega como validación obligatoria al activar un
tipo de reporte (ver ADR-0008).

## Decisión

Almacenar el `.xlsx` original como **plantilla en el servidor** y generar cada reporte abriéndola
con **openpyxl**, escribiendo únicamente los valores en las celdas correspondientes y exportando
sólo la hoja del reporte. El formato (celdas combinadas, bordes, logo, área de impresión, escala)
nunca se construye ni se modifica por código: viaja tal cual dentro de la plantilla.

La plantilla vive exclusivamente en el servidor. El usuario nunca abre ni edita Excel dentro de la
aplicación: completa el formulario guiado definido en el DESIGN (pantallas S-04 a S-08) y recibe
el `.xlsx` ya relleno para descargar.

## Alternativas consideradas

- **Construir el libro desde cero por código con openpyxl** — era viable y evitaría depender de un
  archivo binario externo, dando control total sobre la salida. Se descartó porque obligaría a
  replicar a mano cada celda combinada, borde, ancho de columna, la imagen y la configuración de
  impresión: mucho código frágil dedicado a formato, con alto riesgo de divergencia respecto al
  documento oficial. Con plantilla, la fidelidad es cierta por construcción, ya que el formato
  nunca se toca.

- **Cirugía directa sobre el XML dentro del `.xlsx` (tratarlo como ZIP y reescribir sólo la hoja)**
  — es la única opción que garantiza fidelidad byte a byte de absolutamente todas las partes del
  archivo, incluidas las que openpyxl descarta. Se descartó porque la validación empírica
  demostró que las partes que openpyxl pierde no afectan al documento entregable, y el enfoque
  exige manipular manualmente XML de OOXML (cadenas compartidas, tipos de celda, relaciones), un
  costo de complejidad alto e injustificado frente a un problema que ya está resuelto.

- **LibreOffice headless en el servidor** rellenando y exportando el documento — ofrecería máxima
  fidelidad de renderizado e incluso exportación a PDF. Se descartó por el peso operativo: instalar
  y mantener LibreOffice en el servidor, procesos lentos, consumo de memoria alto y fragilidad de
  despliegue, desproporcionado para un proyecto mantenido por una sola persona.

## Consecuencias

- La fidelidad del formato queda garantizada por construcción, no por esfuerzo de programación:
  lo que no se escribe, no se altera.
- El código de generación se limita a escribir valores en celdas, sin lógica de estilos ni de
  maquetación; es poco código y fácil de leer.
- Se mantiene todo en Python (openpyxl), coherente con la ADR-0001 y con la experiencia del
  desarrollador.
- **Corrección (decisión #4 de RESOLUCION-ADVERSARIAL.md):** el logo es dinámico, dato de
  `TipoDeReporte` (ya lo fijaban el PRD y el TECH-DESIGN): el administrador lo sube desde la
  pantalla S-14, con reemplazo en caliente y *fallback* al logo ya cargado si no sube uno nuevo.
  Esto **sí requiere código**, no es "sin tocar código" como decía una versión anterior de esta
  ADR: al generar el `.xlsx` hay que reemplazar la imagen dentro de la plantilla manipulando
  `ws._images` de openpyxl (quitar la imagen original de la hoja e insertar la del tipo de
  reporte en la misma posición/ancla) antes de escribir los valores.
- **Costo real:** el sistema queda atado a un archivo de plantilla físico. Si el cliente publica
  una revisión del formato oficial, hay que subir el `.xlsx` nuevo y **volver a mapear las
  coordenadas de celda**, porque las filas y columnas pueden haberse desplazado.
- **Costo real:** aparece un artefacto nuevo que hay que definir y mantener: el **mapeo campo →
  celda** (por ejemplo, `turno` → `M12`). Ese mapeo es frágil ante cambios de la plantilla y su
  forma de almacenamiento se decide en la ADR siguiente (plantillas y configuración por tipo de
  reporte).
- **Costo real:** las coordenadas de celda no son autoexplicativas; un error de mapeo produce un
  reporte que parece correcto pero tiene un dato en el lugar equivocado. Esto obliga a una
  verificación campo a campo contra el documento de referencia (ya prevista como criterio de
  éxito en el PRD) y refuerza la necesidad de la prueba automática de archivo dorado (ver
  ADR-0007) como red de seguridad, dado que la revisión previa dentro de la app (S-11/S-12) fue
  eliminada.
