---
title: "Revisión adversarial — Technical Design Document y ADRs"
fecha: "2026-08-25"
alcance: "TECH-DESIGN.md · adrs/0001–0008 · contrastado con PRD.md y DESIGN.md"
metodo: "Revisión adversarial en conversación fresca, sin historial de la generación del diseño"
---

# Revisión adversarial — Generador de Reportes de Campo

Revisión ejecutada en una conversación sin historial de cómo se produjo el diseño, para evitar
que la defensa del propio razonamiento contamine la crítica. `PRD.md` y `DESIGN.md` estaban
disponibles, de modo que el cruce entre documentos es completo. Se leyeron `TECH-DESIGN.md` y
las ocho ADR en su totalidad.

Este documento **reporta**; no modifica `TECH-DESIGN.md` ni ninguna ADR. Qué se corrige y qué se
acepta como costo es decisión humana.

## Índice de hallazgos

| # | Severidad | Hallazgo | Objetivo |
|---|---|---|---|
| 1 | Crítico | Nadie decidió quién renderiza el wizard; el reparto 85/15 no se sostiene | ADR-0001 · ADR-0003 · ADR-0004 |
| 2 | Crítico | `ValorDeReporte` perdió el `rol`; el checklist por rol no entra en el modelo | TECH-DESIGN · ADR-0003 |
| 3 | Crítico | Conflictos de edición concurrente sin resolver, y dados por resueltos | ADR-0004 · ADR-0006 · ADR-0008 |
| 4 | Crítico | El mecanismo del logo se contradice entre documentos | ADR-0002 · TECH-DESIGN |
| 5 | Crítico | La validación empírica no probó la operación que la ADR decide | ADR-0002 |
| 6 | Advertencia | No se consideró Dexie ni Workbox: la mitigación más barata del riesgo principal | ADR-0004 |
| 7 | Advertencia | No se consideró `JSONField` como tercera alternativa | ADR-0003 |
| 8 | Advertencia | Falta por completo la decisión de despliegue, infraestructura y respaldo | Área sin ADR |
| 9 | Advertencia | El correlativo oficial se exige pero no se garantiza | ADR-0004 |
| 10 | Advertencia | La expiración de sesión offline se contradice consigo misma | ADR-0005 |
| 11 | Advertencia | Quién puede dar el visto bueno no está definido de forma ejecutable | ADR-0006 |
| 12 | Advertencia | El Δ se calcula en dos lenguajes sin fuente de verdad | ADR-0002 · ADR-0004 |
| 13 | Advertencia | Adjuntos sin transporte, sin límite y sin almacén decididos | ADR-0004 |
| 14 | Advertencia | Dos contradicciones con el PRD que nadie reconcilió | PRD · TECH-DESIGN |
| 15 | Advertencia | Falta estrategia de pruebas donde ADR-0007 eliminó el otro control | ADR-0007 · Área sin ADR |
| 16 | Sugerencia | Residuo de la vista previa en el sistema de componentes | DESIGN §6 |
| 17 | Sugerencia | `CambioDeValor` crece sin techo ni política de retención | TECH-DESIGN |
| 18 | Sugerencia | El borrador local no registra contra qué versión de la definición se capturó | ADR-0003 · ADR-0004 |

---

## Crítico

### 1. Nadie decidió quién renderiza el wizard. El reparto 85/15 de ADR-0001 no se sostiene

**Dónde:** ADR-0001 (reparto de esfuerzo), ADR-0003 (definición declarativa), ADR-0004 (offline).

ADR-0003 establece que la aplicación "lee esa definición para renderizar el formulario del
wizard". ADR-0004 exige que el formulario completo funcione sin señal. Combinadas, ambas obligan
a que el wizard **se renderice en el cliente**, a partir de una definición cacheada, en
JavaScript. Ninguna ADR lo afirma ni lo decide.

Consecuencias que ningún documento registra:

- La definición declarativa debe viajar al navegador y cachearse. No figura en el contrato de
  endpoints de ADR-0004, que se limita a sincronizar aporte, consultar estado y solicitar
  generación.
- El **intérprete de la definición queda duplicado**: renderizado y validación en JavaScript
  (S-09 debe funcionar offline) y renderizado y validación en Python (el servidor no puede
  confiar en el cliente). Dos implementaciones de la misma gramática, en dos lenguajes,
  mantenidas por una sola persona.
- El 15% de JavaScript deja de ser "service worker, IndexedDB y cola de subida". Pasa a incluir
  un motor de formularios y un motor de validación dirigidos por configuración.

**Por qué importa:** es la mayor subestimación de esfuerzo del documento y recae exactamente
sobre el riesgo que el propio TECH-DESIGN declara principal para el cronograma.

### 2. `ValorDeReporte` perdió el `rol`. Con ese modelo no entra el checklist

**Dónde:** TECH-DESIGN (modelo de datos), ADR-0003.

- ADR-0003: la fila se identifica por `reporte, identificador de campo, rol y usuario`.
- TECH-DESIGN: `reporte, identificador de campo, valor, autor y fecha`. **Sin rol.**

El formato de referencia verifica el mismo ítem desde dos roles en columnas separadas
(Consorcio JME / QA Subterra en parámetros preliminares; QC JME / QA Antamina en resultados).
Sin `rol` en la identidad del valor, el ítem `p-01` admite un único valor y las dos columnas
colisionan.

El ejemplo YAML de ADR-0003 arrastra el mismo problema: declara `roles: [construccion-jme,
qa-subterra]` a nivel de sección, pero define un solo par `celda_inicio` / `celda_fin` por ítem.
No hay forma de expresar dos celdas de destino, una por rol.

**Decisión pendiente:** incorporar `rol` a la clave del valor, o cualificar los identificadores
de campo por rol. El mapeo campo → celda cambia según cuál se elija.

### 3. Conflictos de edición concurrente: sin resolver, y ADR-0008 los da por resueltos

**Dónde:** ADR-0004, ADR-0006, ADR-0008.

ADR-0008 afirma: "Los fallos de sincronización ya quedaron resueltos en la ADR-0004". Es
inexacto. ADR-0004 resuelve **duplicados por reintento del mismo dispositivo** mediante
idempotencia por ID local. No resuelve dos participantes editando el mismo reporte.

ADR-0006 abrió la edición: cualquier invitado puede editar cualquier sección, incluida la de
otro rol. ADR-0004 sincroniza bloques completos por sección. Cruzadas, ambas decisiones
producen: dos invitados editan la misma sección sin conexión, ambos sincronizan, gana el último
en llegar, en silencio, y `CambioDeValor` registra la sobrescritura como una edición normal e
indistinguible. El PRD nombró "conflictos" como riesgo explícito del modo offline. Ninguna ADR
lo cierra.

Queda además una pregunta previa sin responder: **¿puede un invitado trabajar offline sobre un
reporte ajeno?** El service worker cachea el app shell y los recursos estáticos, no los datos
del reporte. Sin cachear también los datos, la colaboración es online-only y ADR-0006 contradice
el principio del DESIGN de que "offline es el caso normal, no la excepción".

### 4. El mecanismo del logo se contradice entre ADR-0002 y TECH-DESIGN

**Dónde:** ADR-0002, TECH-DESIGN (modelo de datos y criterios de aceptación), PRD, DESIGN S-14.

- ADR-0002: "Cambiar el logo institucional es reemplazar una imagen en la plantilla, sin tocar
  código". El logo viaja dentro del `.xlsx` y nunca se manipula.
- TECH-DESIGN, PRD y S-14: el logo es un dato de `TipoDeReporte`, el administrador lo sube desde
  la interfaz y el documento generado cambia.

Son dos mecanismos incompatibles. El segundo obliga al generador a **eliminar la imagen de la
plantilla ya cargada y anclar otra** (`ws._images` en openpyxl), replicando a mano su tamaño,
posición y anclaje. Eso es código, y es precisamente el tipo de manipulación de formato que
ADR-0002 se comprometió a no hacer.

**Consecuencia directa:** el criterio de aceptación "reemplazar el logo en el tipo de reporte
cambia el logo del documento sin tocar código" no es cumplible tal como está redactado.

### 5. La validación empírica de ADR-0002 no probó la operación que la ADR decide

**Dónde:** ADR-0002 (validación empírica), TECH-DESIGN (misma tabla), ADR-0008 (validación
anticipada).

El experimento realizado fue abrir el archivo con openpyxl y volver a guardarlo. La decisión que
la ADR toma es abrir la plantilla, **escribir valores en celdas**, **exportar sólo la hoja del
reporte** y guardar. Se validó el paso que no concentraba el riesgo.

Dos modos de fallo concretos que un round-trip no puede detectar:

**Celdas combinadas.** En openpyxl, toda celda de un rango combinado que no sea la ancla
superior-izquierda es un `MergedCell` de sólo lectura; escribir en ella lanza excepción. Con 64
rangos combinados y un mapeo campo → celda escrito a mano, el caso se va a presentar. La
validación anticipada de ADR-0008 comprueba "referencias de celda con formato válido y sin
colisiones", pero **no comprueba que la celda de destino sea la ancla de su rango combinado**.
Esa es la regla de validación que falta.

**Fórmulas.** openpyxl descarta los valores cacheados de fórmula al guardar. Si la plantilla
calcula tiempos transcurridos o totales mediante fórmula, el archivo abre correctamente en Excel
—que recalcula— pero el criterio de aceptación "se verifica contra el archivo de referencia
celda por celda", leído con `data_only=True`, devuelve `None`. La verificación que ADR-0007
designó como **único control existente** no funciona hasta que esto se decida.

Nada de esto invalida la decisión de generar sobre plantilla. Invalida la afirmación de que el
riesgo señalado por el PRD "queda acotado": todavía no lo está.

---

## Advertencia

### 6. ADR-0004 no consideró Dexie ni Workbox, la mitigación más barata del riesgo principal

La propia ADR reconoce que IndexedDB tiene "una API asíncrona y verbosa, claramente más difícil
que `localStorage` para quien no domina JavaScript", y el TECH-DESIGN declara esa capa el riesgo
principal de cronograma. Las alternativas evaluadas fueron `localStorage`, sincronización campo
por campo y Background Sync API. **Ninguna de las tres reduce esa dificultad.**

Dexie.js para IndexedDB y Workbox para el service worker son una etiqueta `<script>` cada uno y
no requieren build pipeline, de modo que no violan la restricción de ADR-0001, que prohíbe
*frameworks de frontend*, no bibliotecas. Eliminan buena parte del código más difícil del
proyecto.

La ADR aceptó el riesgo sin evaluar la opción que lo reduce. El conjunto de alternativas es
incompleto en el eje que más importa.

### 7. ADR-0003 no consideró `JSONField` como tercera alternativa

Las dos alternativas presentadas son extremos opuestos: columnas fijas por tipo de reporte, o
almacenamiento genérico tipo EAV. Falta la intermedia: definición declarativa idéntica, con los
valores en un `JSONField` de PostgreSQL sobre `Reporte`.

Esa opción cumple el criterio de éxito del PRD exactamente igual, es nativa en Django, indexable
en PostgreSQL, y evita el join sobre la tabla genérica de valores que la propia ADR admite como
costo. El contrapeso real es que la autoría por valor —necesaria para `CambioDeValor` y para
mostrar "quién completó cada celda" en S-05— encaja peor en un documento JSON.

Ese es exactamente el argumento que la ADR debía dar para descartarla, y no lo da porque no la
menciona.

### 8. Falta por completo la decisión de despliegue, infraestructura y respaldo

No existe ADR de hosting, HTTPS, PostgreSQL frente a SQLite, almacén de archivos (disco local
frente a almacenamiento de objetos) ni **respaldos**. El diagrama de componentes dibuja
PostgreSQL y un "Almacén de archivos" sin que ninguna decisión los justifique.

Dos elementos duros quedan sin registrar:

- **El service worker exige HTTPS.** Es un requisito de plataforma, no una preferencia de
  seguridad. Sin él, ADR-0004 no arranca.
- Todo el valor del sistema es el repositorio de reportes emitidos. Sin política de respaldo, un
  fallo de disco elimina el producto. Ese es el hueco natural de una ADR de resiliencia, y
  ADR-0008 cubre únicamente errores de aplicación.

### 9. El correlativo oficial se exige en los criterios pero no se garantiza en ninguna decisión

Criterio de aceptación vigente: "Dos dispositivos que sincronizan reportes creados sin conexión
reciben números distintos y correlativos, sin colisión".

Eso no se obtiene por defecto: requiere `select_for_update` o una secuencia de base de datos
dentro de la transacción de sincronización. Con un `max() + 1` ingenuo, dos peticiones
simultáneas producen el mismo número de registro. Ninguna ADR nombra el mecanismo.

Falta además la restricción `unique` sobre `Reporte.id_local`: la idempotencia depende de esa
restricción de base de datos, no del código de la vista.

### 10. La expiración de sesión offline se contradice consigo misma

ADR-0005 mitiga el robo de dispositivo con "una expiración local razonable de la sesión
cacheada". La misma ADR descarta exigir conexión para iniciar sesión porque "el usuario que
llega al frente de trabajo sin señal no podría siquiera abrir la aplicación".

Si la expiración local vence en turno y sin señal, ocurre exactamente eso: usuario bloqueado,
con el borrador atrapado en un dispositivo al que ya no puede entrar.

**Decisión pendiente:** el valor concreto de la expiración y el comportamiento al vencer sin
conexión (¿acceso de sólo lectura? ¿PIN local? ¿ninguna expiración y se asume el riesgo?). Hoy
no hay ni valor ni comportamiento definidos.

### 11. Quién puede dar el visto bueno no está definido de forma ejecutable

- DESIGN S-10: botón "Marcar como terminado" **reservado al responsable de revisión**.
- ADR-0006: "un usuario responsable revisa el reporte y lo marca explícitamente como terminado".
- Modelo de datos: `VistoBueno` guarda usuario y fecha; `ParticipacionEnReporte` no tiene ningún
  campo de responsabilidad.

Sin ese campo, cualquier invitado puede cerrar el reporte, y la revisión humana deliberada que
ADR-0006 presenta como beneficio del cierre manual queda sin mecanismo que la sostenga.

ADR-0006 arrastra un pendiente hermano que tampoco resuelve: "conviene prever que un
administrador pueda intervenir" cuando el creador olvida compartir el reporte. El PRD lo lista
como caso borde a contemplar; sigue sin contemplarse.

### 12. El Δ se calcula en dos lenguajes sin fuente de verdad declarada

S-06 exige el Δ calculado en vivo en el navegador, en JavaScript, funcionando sin conexión. El
`.xlsx` necesita el tiempo transcurrido en su celda de destino: o lo escribe Python al generar,
o lo calcula una fórmula que ya vive en la plantilla. Tres implementaciones posibles y ninguna
elegida.

El PRD exige coincidencia del **100%** con el cálculo manual esperado. Dos implementaciones
independientes divergen en redondeo, en el tratamiento del cruce de medianoche y en la
representación del resultado.

**Decisión pendiente:** designar una fuente de verdad y que las demás la copien, en lugar de
recalcular.

### 13. Adjuntos: sin transporte, sin límite y sin almacén decididos

ADR-0004 envía el bloque de rol completo "en una sola operación" a través de endpoints **JSON**,
e incluye las imágenes en ese envío. Eso implica base64 —con un recargo aproximado del 33% sobre
la peor conectividad del proyecto— o multipart. La decisión no se toma.

Además:

- El límite de tamaño que el DESIGN exige mostrar al usuario antes de adjuntar no tiene valor
  definido en ningún documento.
- La compresión en el dispositivo aparece dos veces como recomendación ("conviene comprimirlas")
  y nunca como decisión con parámetros.
- El "Almacén de archivos" del diagrama no tiene tecnología asignada.

### 14. Dos contradicciones con el PRD que nadie reconcilió

ADR-0006 incluye una sección "Impacto sobre documentos previos" y actualiza el PRD y el DESIGN
en consecuencia. Estas dos contradicciones no recibieron el mismo tratamiento:

**PRD, "No alcance":** "No incluye historial/repositorio central de reportes generados, búsqueda
ni reportes de gestión sobre reportes pasados". Sin embargo, S-02 incluye buscador y filtros
sobre "mis reportes", y el modelo de datos persiste `Generacion` y el historial completo en el
servidor. O el "No alcance" está obsoleto, o S-02 excede el alcance. Sigue sin resolverse.

**PRD, "Supuestos y riesgos abiertos":** "El reporte 'vive' en el servidor desde que se crea; las
secciones se llenan online". El ciclo de vida del TECH-DESIGN comienza en `borrador local`, que
por definición no vive en el servidor. Contradicción directa con el supuesto declarado.

### 15. Falta estrategia de pruebas justo donde ADR-0007 eliminó el otro control

ADR-0007 declara que la verificación campo a campo contra el documento de referencia, al activar
cada tipo de reporte, es "el único control de corrección del mapeo", y la deja como acto manual.

Con 64 rangos combinados, alrededor de 18 campos de cabecera y unos 25 ítems de checklist, una
verificación manual que se ejecuta una vez por tipo de reporte se hace peor la segunda vez y no
se repite tras un cambio de plantilla.

Lo que corresponde es una prueba de archivo dorado: un reporte de datos fijos, generar y
comparar celda a celda contra un `.xlsx` esperado versionado en el repositorio. Es la red que
convierte los costos asumidos en ADR-0002 y ADR-0007 en algo sostenible por una sola persona.
Ninguna ADR la decide.

---

## Sugerencia

### 16. Residuo de la vista previa en el sistema de componentes

`DESIGN.md`, sección 6, sigue listando `Placeholder de imagen | Adjuntos y vista previa del
documento`. Es un residuo de S-11 y S-12, eliminadas por ADR-0007.

### 17. `CambioDeValor` crece sin techo ni política de retención

Una fila por escritura, y ADR-0006 hace obligatorio el registro en cada edición. Sin política de
retención ni índice declarado, la vista de historial de S-10 se degrada con el tiempo. Es barato
de decidir ahora y molesto de corregir después.

### 18. El borrador local no registra contra qué versión de la definición se capturó

`Generacion` guarda la versión de plantilla utilizada; el borrador local, no. Si el
administrador reactiva un tipo de reporte con celdas o campos desplazados mientras existen
borradores locales sin sincronizar, esos borradores quedan mapeados contra una definición que ya
no existe.

---

## Lo que aguantó la revisión

No se inventaron hallazgos donde el diseño se sostiene:

- **ADR-0007 (sin vista previa)** es coherente y honesta. Ofreció tres niveles de fidelidad, el
  usuario eligió el más barato, y la ADR registra el costo sin maquillarlo, incluida la molestia
  de revisar un `.xlsx` desde un celular.
- **ADR-0008 (Sentry)** es proporcionada. El argumento contra `mail_admins` es concreto y
  correcto —credenciales SMTP, clasificación como spam, un correo por ocurrencia— y descartar el
  reintento automático porque los fallos previstos son deterministas es razonamiento sólido.
- **ADR-0005 (sesiones de Django)** acierta. Descartar JWT sin una frontera de API pública es la
  lectura correcta: ahí sólo agregaría trabajo de gestión de expiración y almacenamiento.
- **ADR-0001** no está sobre-diseñada. El argumento de que agregar offline más tarde no sería
  agregar una función sino rehacer la capa de formulario es verdadero, y es la razón correcta
  para pagar ese costo hoy. El problema no es la decisión, sino que su estimación de esfuerzo
  (hallazgo 1) no refleja lo que la decisión implica.

---

## Recomendación de orden

Los cinco hallazgos críticos bloquean la implementación, no el diseño:

1. **Hallazgo 5 primero.** Media hora de prueba real —escribir valores en las anclas de los 64
   rangos combinados y exportar sólo la hoja del reporte— confirma o derrumba la premisa central
   de ADR-0002 antes de que cualquier otra cosa dependa de ella.
2. **Hallazgos 2 y 4** son contradicciones internas: hay que resolverlas antes de escribir el
   modelo de datos y el generador.
3. **Hallazgos 1 y 3** cambian el tamaño del proyecto. Conviene decidirlos antes de comprometer
   fechas.
