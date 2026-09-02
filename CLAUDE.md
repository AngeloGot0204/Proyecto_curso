# Generador de Reportes de Campo

Aplicación web para completar reportes de instalación en faena y generar el `.xlsx`
final sobre la plantilla original de la empresa. Se usa en terreno, sin señal, desde un
celular. Lo que se entrega al cliente es el Excel, no la pantalla.

## Lo primero que hay que entender

**Un tipo de reporte no se programa: se configura.** Cada uno se define en un YAML
declarativo que dice qué secciones y campos tiene, y a qué celda del `.xlsx` va cada
valor. Agregar un tipo de reporte nuevo **no debe tocar código**.

Si te encontrás escribiendo un `if` sobre el código de un tipo de reporte, parate: el
diseño está diciendo que eso va en el YAML. `tipos_reporte/` es el corazón del proyecto,
no `reportes/`.

## Stack

Django 5.2 · Python 3.12 · PostgreSQL (Neon) · openpyxl · JavaScript vanilla sin build
step · Vercel + Vercel Blob · Sentry.

**Sin framework de frontend, sin build step, a propósito** (ADR-0001). Es server-rendered
con JS vanilla. No propongas React, Vite ni un bundler: la decisión está tomada y
justificada por el riesgo de cronograma de un desarrollador solo.

## Dónde vive cada cosa

```
config/          Settings, URLs raíz, CSP, storage de Vercel Blob
usuarios/        Usuario custom, roles, autenticación
tipos_reporte/   Motor de definiciones YAML, validador, generador de Excel
reportes/        Wizard de captura, validación, cierre, adjuntos, capa offline
openspec/specs/  Contrato vigente de cada capacidad — la fuente de verdad
adrs/            Por qué se decidió cada cosa, y qué se descartó
```

**`openspec/specs/` describe el comportamiento esperado HOY.** Si vas a cambiar
comportamiento, la spec cambia con el código, en el mismo PR. Una spec que miente es peor
que no tenerla.

## Convenciones que no son negociables

**Español para el dominio, inglés para lo técnico.** Modelos, campos, funciones y
variables de negocio en español (`Reporte`, `ValorDeReporte`, `guardar_valor`,
`tiene_acceso`). Docstrings y comentarios en inglés. No es capricho: el dominio es de
faena peruana y traducirlo pierde precisión.

**Docstrings que explican el PORQUÉ, no el qué.** El código ya dice qué hace. Los
docstrings de este repo dicen por qué se eligió eso y qué alternativa se descartó,
citando la ADR o la spec. Cuando escribas uno, seguí ese estándar — mirá
`reportes/views.py::_reporte_accesible` o `tipos_reporte/generador.py::_neutralizar_formula`
como referencia.

**Acumular errores, nunca cortar en el primero.** El validador de definiciones recorre
el YAML entero y devuelve todos los problemas juntos. Un administrador no debería
descubrir sus errores de a uno, subiendo el archivo diez veces.

**Fail-loud sobre default silencioso.** `require_env()` y `require_bool_env()` revientan
al arrancar si falta o está mal una variable. `DJANGO_HTTPS_ONLY` acepta exactamente
`True` o `False` — `true`, `1` y `yes` se rechazan, para que un typo no apague las
protecciones de transporte sin que nadie lo note.

**Un solo dueño por dato.** El host de Vercel Blob vive solo en `config/storage.py`; la
CSP lo importa. `claves_de_valor()` es el único lugar que deriva los identificadores de
campo, y lo usan tanto el wizard como el generador. Hay un test (`test_a7`) que falla si
alguien duplica el host.

## Testing

**TDD estricto: el test se escribe en rojo primero, y hay que verlo fallar.**

Esto no es ceremonia. En este proyecto ya pasó dos veces que un test pasaba en verde sin
probar nada — una regex con un byte de control que no matcheaba nunca. Si no viste el
rojo, no sabés qué está midiendo tu test.

```bash
pytest                                   # todo (~19 min, necesita Postgres real)
pytest reportes/tests/test_views.py      # un archivo
pytest -k "cerrar or chip"               # por nombre
```

La suite usa `--reuse-db`. Si cambiaste migraciones, agregá `--create-db`.

**Los tests necesitan PostgreSQL de verdad**, no SQLite: el proyecto usa `db_default` con
`gen_random_uuid()` y `nextval()`, y `CheckConstraint` a nivel de motor.

**Verificá contra qué base apuntás antes de correr nada.** `DATABASE_URL` debe ir a la
rama `dev` de Neon. Ya ocurrió que el entorno local apuntara a producción y las bases de
test se crearan ahí.

## Trampas de este proyecto

**openpyxl deduce el tipo de celda del string.** Un valor que empieza con `=` se
serializa como fórmula viva. Todo valor capturado se escribe como texto vía
`_neutralizar_formula`. No lo saques.

**El almacenamiento cambia según `DEBUG`.** Con `DEBUG=True` es el disco local, con
`False` es Vercel Blob. La misma columna guarda una ruta relativa o una URL completa
según cuál escribió. Si subís archivos desde local contra una base compartida, quedan
referencias que solo funcionan en tu máquina. `scripts/reparar_referencias_de_archivo.py`
existe por eso.

**Escribir en una celda no-ancla de un rango combinado revienta openpyxl.** El validador
lo verifica antes de aceptar una definición.

**Las migraciones no corren solas** — ni en el build ni en un request. Se aplican a mano
contra Neon antes de depender del esquema nuevo (ADR-0009). Hay un test que falla si
alguien las automatiza.

**El service worker es un template de Django, no un estático.** Nunca escribas el token
`{#` dentro de `sw.js`.

## Seguridad

`SECURITY-REPORT.md` tiene el pase completo con 14 hallazgos, su estado y su triage.
Antes de tocar adjuntos, generación o autenticación, leelo: varios findings siguen
abiertos por decisión explícita del dueño del producto, no por olvido.

Lo que está cerrado y no hay que romper: neutralización de fórmulas, strip de metadatos
EXIF en las fotos, librerías de terceros vendorizadas en `static/vendor/` con SHA-256
registrado, y CSP sin `unsafe-inline` — que solo se sostiene mientras ninguna plantilla
tenga JavaScript inline. Hay un test que lo vigila.

## Harness propio

`.agents/skills/` — dos skills escritas para este proyecto:

- **`generar-backlog`** — despieza un PRD + Technical Design en un backlog ordenado de
  specs, cada una lista para arrancar un ciclo SDD.
- **`revision-adversarial`** — revisa un Technical Design y sus ADRs buscando huecos y
  decisiones débiles, en vez de validarlas. Su salida está en
  `REVISION-ADVERSARIAL.md`, y las decisiones que resolvió, en
  `RESOLUCION-ADVERSARIAL.md`.

## Flujo de trabajo

El proyecto usa **SDD (Spec-Driven Development)**: cada cambio pasa por proposal → spec →
design → tasks → apply → verify → archive, y queda en `openspec/changes/archive/`. Hay 19
ciclos completos ahí.

**No todo cambio necesita SDD.** Un arreglo puntual con requisito obvio se implementa
directo, con su test. SDD se usa cuando la ambigüedad es real y los artefactos durables
la reducen.

Commits en **conventional commits**, en español, explicando el porqué del cambio y no
solo el qué.
