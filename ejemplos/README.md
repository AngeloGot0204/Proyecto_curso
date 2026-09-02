# Ejemplos

Material mínimo para probar el sistema en una instalación limpia. La aplicación
arranca sin tipos de reporte cargados: sin esto no hay nada que completar.

## `instalacion-resinas.yaml`

Definición del tipo de reporte «Verificación de Instalación de Pernos de Anclajes
con Resina», derivada del formato real `JME.PC-0001.F1`. Declara las secciones y
campos del reporte, la celda de destino de cada valor, y dos anclajes de adjuntos
(`B51` y `M51`) que corresponden a los recuadros de croquis y observaciones de la
plantilla.

**La plantilla `.xlsx` no está en el repositorio**: es un formato de una empresa y
no corresponde versionarlo acá. Para probar el flujo hace falta un `.xlsx` cuya
hoja se llame `JME.PC-0001.F1` y cuyas celdas destino existan; el validador rechaza
la definición si no coinciden, indicando exactamente qué falta.

## Cómo usarlo

1. Iniciar sesión como administrador.
2. Tipos de reporte → Nuevo → cargar la plantilla `.xlsx`.
3. Nueva definición → cargar este YAML → Activar.
4. Ya se pueden crear reportes de ese tipo.
