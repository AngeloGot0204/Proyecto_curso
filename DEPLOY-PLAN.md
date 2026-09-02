# Deploy Plan — Generador de Reportes de Campo

Fecha: 2026-09-01
Estado: **DISEÑADO — CON BLOQUEANTES**. Nada ejecutado, nada generado.

> **Leer primero la sección "Hallazgos de la inspección con Vercel CLI".** Dos de ellos
> bloquean el objetivo del despliegue, y ninguno se ve desde el repositorio: hicieron
> falta credenciales reales para descubrirlos. El plan de release que sigue más abajo es
> correcto en su mecánica, pero desplegar sin resolver esos dos primero publica algo que
> nadie fuera del equipo puede usar.

## Resumen del proyecto

Django 5.2 sobre Python 3.12, server-rendered, sin build step de frontend. PostgreSQL en
**Neon**, hosting en **Vercel** (plan Hobby, dominio `proyecto-curso.vercel.app`),
archivos en **Vercel Blob**, errores en **Sentry**. Repo en GitHub
(`AngeloGot0204/Proyecto_curso`), proyecto de Vercel ya vinculado
(`.vercel/project.json`).

**No existe CI/CD.** No hay `.github/workflows/`, ni GitLab CI, ni Jenkins, ni CircleCI.
La única automatización es la integración Git nativa de Vercel.

Este deploy en particular es **solo código**: cero cambios de modelo, cero migraciones
nuevas. Eso elimina de raíz el riesgo más caro de cualquier despliegue Django.

## Lo que ya está verificado (no supuesto)

| Verificación | Resultado |
|---|---|
| Suite completa en Python 3.12 (versión de producción) | **520 passed, 0 failed** |
| Suite completa en Python 3.14 (entorno local) | 520 passed, 0 failed |
| `manage.py check --deploy --fail-level WARNING` | **exit 0**, sin issues (1 silenciado a propósito: `security.W021`) |
| `manage.py collectstatic --noinput` (el build real de Vercel) | **148 archivos**, 146 post-procesados, sin error |
| Migraciones pendientes | **ninguna** — `git status` no muestra ningún archivo en `*/migrations/` y ningún `models.py` cambió |

## Hallazgos de la inspección con Vercel CLI

Verificados el 2026-09-01 con `vercel project inspect`, `vercel env ls`, `vercel ls`,
`vercel inspect --logs` y peticiones HTTP a los dominios reales. Solo lectura: no se
ejecutó ningún comando que cree, modifique o borre, y **no se corrió `vercel env pull`**,
que habría escrito los valores reales de los secretos en el disco.

### D-1 — BLOQUEANTE: producción no es accesible públicamente

`https://proyecto-curso-dmc-gotuzzo.vercel.app/login/` responde **302** hacia
`https://vercel.com/sso-api?...`. La **Deployment Protection** de Vercel está activa:
solo alguien con sesión iniciada en el equipo de Vercel puede abrir la aplicación.

Un usuario en faena —el único usuario que este producto tiene— recibe la pantalla de
login de Vercel, no la de la aplicación.

Esto contradice de forma directa el primer requisito de la spec
`despliegue-e-infraestructura`:

> **HTTPS Reachability** — "The deployed application MUST be reachable over HTTPS at
> Vercel's default `<project>.vercel.app` domain"

Ese requisito tiene su escenario marcado como *Manual (live)*, es decir, dependía de que
una persona lo verificara a mano. Nadie lo hizo, o se hizo con una sesión de Vercel
abierta —que es justamente lo que enmascara el problema.

**Acción:** desactivar Deployment Protection para Production en el panel de Vercel
(Settings → Deployment Protection). Es una decisión tuya y no la ejecuto sin permiso.
Considerá dejarla ACTIVA para Preview: ahí sí tiene sentido, porque evita que un preview
con datos de prueba quede indexable.

### D-2 — BLOQUEANTE: el dominio que la spec nombra es de otro proyecto

`https://proyecto-curso.vercel.app/` devuelve **200** con este contenido:

```html
<title>React Criptomonedas</title>
<script type="module" src="/assets/index.1dab87d1.js"></script>
```

Es una aplicación Vite/React distinta, servida desde el CDN (`X-Vercel-Cache: HIT`,
`Content-Length: 459`). El subdominio corto está tomado por otro proyecto de la misma
cuenta.

El dominio real de esta aplicación es `proyecto-curso-dmc-gotuzzo.vercel.app`.
`vercel domains ls` devuelve **0 dominios personalizados**.

**Consecuencia a verificar antes de desplegar:** si `DJANGO_ALLOWED_HOSTS` en Production
contiene `proyecto-curso.vercel.app`, Django rechazará toda petición al dominio real con
`DisallowedHost`. No pude comprobarlo sin leer el valor del secreto, cosa que
deliberadamente no hice. **Revisalo vos en el panel**: debe contener el host real, y
`DJANGO_CSRF_TRUSTED_ORIGINS` debe contener `https://` + ese mismo host.

Mientras D-1 esté activo, este error queda enmascarado: el SSO intercepta la petición
antes de que llegue a Django.

### D-3 — Sentry no está configurado en ningún entorno

`vercel env ls` no muestra `SENTRY_DSN` en Production, Preview ni Development.

`config/settings.py` activa Sentry solo si el DSN existe. No existe. Por lo tanto
**producción no está capturando ningún error**, y el `logger.exception` de
`views.generar` no llega a ninguna parte.

El backlog #14 figura como `✓ DONE` y el código es correcto — pero el interruptor nunca
se encendió. La observabilidad está implementada y apagada.

**Acción:** crear un proyecto en Sentry y agregar `SENTRY_DSN` a Production. Sin esto, el
punto "Verify & Observe" de este plan que decía *"mirar Sentry las primeras horas"* era
una instrucción vacía.

### D-4 — Producción deriva la versión de Python del rango, porque el `.python-version` nunca se desplegó

> **Corrección.** La primera versión de este hallazgo decía que Vercel ignoraba un
> `.python-version` commiteado. Es falso y lo verifiqué después: el archivo **no existe
> en `main`**. Se agregó en el commit `c5519c6`, en la rama actual, que nunca se
> desplegó. Vercel se comportó correctamente.

Log del build de producción:

```
Using Python 3.12 from pyproject.toml
Writing .python-version file with version 3.12
```

Vercel no encontró el archivo y cayó en su fallback: derivar la versión del
`requires-python = ">=3.12"` de `pyproject.toml`, tomando el **límite inferior**.

O sea: **hoy, el código que corre en producción no tiene la protección que la spec
diseñó.** El resultado es correcto (3.12) sólo porque el límite inferior coincide. Si
alguien ampliara el rango a `">=3.10"`, producción se movería a Python 3.10 en silencio
— exactamente el escenario que la spec advierte:

> "Without that file, Vercel resolves the version from `requires-python` in
> `pyproject.toml` by taking the lower bound of the range."

**Buena noticia:** el merge de esta rama lleva el archivo a producción y cierra el hueco.

**Acción:** después del primer deploy con la rama mergeada, **leer el log de build y
confirmar** que ahora dice que toma la versión del `.python-version`. No darlo por hecho:
el escenario de la spec ("the build log reports the version matching `.python-version`")
nunca se verificó, y así fue como esto pasó desapercibido. Complemento útil: endurecer
`requires-python` a `">=3.12,<3.13"` para que el fallback también sea correcto.

### D-11 — El merge no despliega "los arreglos de hoy": despliega 15 commits sin publicar

`git rev-list --left-right --count origin/main...HEAD` → **0 / 15**.

La rama está 15 commits adelante de `main`, y **ninguno está en producción**. Entre
ellos hay trabajo funcional real, no sólo documentación:

```
e1d17e1 fix(generacion): autora la plantilla desde codigo y repara dos defectos
a3f146c feat(offline): agrega Sincronizacion al sidebar
eaee70f fix(offline): preserva los metadatos del borrador al reintentar un envio
e11a548 feat(offline): completa el chip de conexion en toda pantalla con barra
002103b fix(reportes): corrige callejon sin salida al cerrar y doble creacion
c5519c6 build: fija la version de Python explicitamente en .python-version
```

Esto cambia el tamaño del despliegue. No es "publicar unos arreglos de seguridad": es
publicar **quince commits de trabajo acumulado más los arreglos de seguridad**, de una
sola vez, sobre una aplicación que nadie está usando hoy.

Que nadie la use hoy (ver D-1) baja el riesgo real. Pero la verificación en preview deja
de ser un trámite: hay que probar el flujo completo, no sólo lo que tocamos hoy.

### D-12 — La base de producción se está usando como banco de pruebas

Contenido real de `neondb` en la rama de producción:

| Tabla | Filas |
|---|---|
| Usuarios | 2 |
| Tipos de reporte | 2 |
| Definiciones | 6 |
| **Reportes** | **20** (17 borrados lógicamente) |
| Adjuntos | 6 |
| Generaciones | 3 |

Primer reporte 2026-08-30, último 2026-09-01 13:44 (hora local). 17 de 20 borrados: es el
patrón inconfundible de pruebas manuales, no de uso real — y no podría ser uso real,
porque nadie puede entrar a la aplicación desplegada (D-1).

Combinado con D-8: no es sólo que las bases de test se crean en la rama de producción.
Es que **`neondb` de producción es, en los hechos, la base de desarrollo**.

Consecuencias concretas:
- Los datos "de producción" son datos de prueba. Sirve saberlo antes de decidir cualquier
  cosa sobre respaldos o migraciones.
- Cuando la aplicación se abra a usuarios reales, esos 20 reportes de prueba van a estar
  ahí conviviendo con los de verdad, salvo que se limpien antes.
- La rama `dev` existe, está lista, y no se está usando.

### D-13 — El `DATABASE_URL` local no usa el endpoint con pooler

Host al que conecta la configuración local:

```
ep-icy-firefly-ax9w17zr.c-4.us-east-2.aws.neon.tech
```

Sin el sufijo `-pooler`. La spec exige el endpoint agrupado:

> **Neon Pooled Endpoint With CONN_MAX_AGE=0** — "Production `DATABASE_URL` MUST use
> Neon's `-pooler` hostname"

**Alcance de lo que verifiqué, dicho con precisión:** esto es la configuración **local**,
no la de Vercel. No leí el valor del secreto de Production, así que **no puedo afirmar
que producción tenga el mismo problema**. Lo que sí queda demostrado es que existe al
menos una configuración activa que incumple el requisito, y que ese requisito nunca se
verificó de forma ejecutable — su escenario está marcado *Manual (console)*.

**Acción:** revisá el valor de `DATABASE_URL` en Production en el panel y confirmá que
el host lleve `-pooler`. Sin eso, con `CONN_MAX_AGE = 0`, cada request abre una conexión
directa contra Postgres y el pool se agota bajo concurrencia — que es justo el fallo que
la decisión de ADR-0009 buscaba evitar.

### D-5 — Las dependencias se instalan desde `pyproject.toml`, no desde `requirements.txt`

Mismo log: `Installing required dependencies from pyproject.toml...`

Aunque el panel del proyecto declara `Install Command: pip install -r requirements.txt`,
el builder de Python detecta `pyproject.toml` y lo usa.

Verifiqué que hoy las dos listas son **idénticas** (11 dependencias, mismos rangos). Pero
son dos fuentes de verdad para lo mismo: agregar una dependencia solo a
`requirements.txt` la instalaría en tu máquina y **nunca** en producción, con un fallo
que aparece recién en runtime.

Esto además reubica el arreglo de `SECURITY-REPORT.md` F-07: el lockfile tiene que
gobernar lo que Vercel instala de verdad, o no sirve de nada.

### D-6 — `BLOB_READ_WRITE_TOKEN` está guardado como "Config", no como "Secret"

En `vercel env ls`, las tres variables del Blob store aparecen con tipo **Config** y su
valor visible en el listado, mientras que las de Django figuran como **Secret / Hidden**.

Es como las provisiona la integración de Vercel Blob, no un error tuyo. Pero ese token da
lectura y escritura sobre todos los archivos subidos —incluidas las fotos de faena— y hoy
se puede leer desde el panel y desde el CLI sin ninguna fricción.

**Acción sugerida:** revisar si Vercel permite marcarlo como Sensitive. Si no, tratarlo
como lo que es: un secreto de producción con visibilidad más amplia de lo ideal.

### D-7 — El HSTS que llega al navegador es el de Vercel, no el de Django

Respuesta real de producción:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

`config/settings.py` configura `SECURE_HSTS_SECONDS = 3600` y `SECURE_HSTS_PRELOAD =
False`, con un comentario que explica por qué el preload no corresponde en un sufijo
público como `vercel.app`.

Vercel envía su propio HSTS en el borde: **2 años y con `preload`**. El razonamiento
documentado en el código es correcto pero **inoperante** — el navegador recibe otra cosa.

No es un riesgo (el HSTS de Vercel es más estricto, no menos). Es una divergencia entre
lo que el código dice que hace y lo que realmente ocurre, y quien lea `settings.py`
creyendo que ahí está la última palabra se va a equivocar. Vale una nota en ADR-0009.

### D-8 — Los tests locales corren contra la rama de PRODUCCIÓN de Neon

Bases de datos existentes por rama:

| Rama Neon | Bases |
|---|---|
| `production` (default) | `neondb`, **`test_reportes_dev`**, **`test_reportes_py312`** |
| `dev` | `neondb`, `test_reportes_dev` |

La rama `production` contiene dos bases de test. Eso solo puede pasar si el
`DATABASE_URL` del `.env` local apunta a la rama de producción: cada `pytest` crea su
base de test **ahí**.

**Mi parte en esto, explícita:** durante la auditoría de seguridad corrí la suite
completa cinco veces sin verificar antes a qué rama apuntaba `DATABASE_URL`. Cuatro
corridas reutilizaron `test_reportes_dev` sobre producción, y la quinta creó
`test_reportes_py312` (2026-09-01T23:50Z) al fijar `TEST_DB_NAME` para la verificación en
Python 3.12. Debí comprobarlo antes de la primera corrida y no lo hice.

**Lo que NO ocurrió, dicho con precisión y no como excusa:** `pytest-django` crea siempre
una base separada con prefijo `test_` y nunca escribe en `neondb`. Los datos de
producción no se modificaron ni corrieron riesgo de modificarse.

**Lo que sí ocurrió:** esas bases consumen el límite de 512 MB por rama que comparten con
los datos de producción, y cada corrida gastó tiempo de cómputo del endpoint de
producción (el proyecto acumula 42 448 s activos y 10 746 s de CPU; una parte es mía).

**El hueco de diseño de fondo, que es anterior a mí:** la rama `dev` existe exactamente
para esto y el desarrollo local no la está usando. La spec `despliegue-e-infraestructura`
prevé que los previews compartan la rama dev, pero nada dice ni verifica a dónde apunta
el `.env` de una máquina de desarrollo — y el default terminó siendo producción.

**Acciones sugeridas:**

1. Apuntar el `DATABASE_URL` del `.env` local a la rama **dev**, no a producción.
2. Borrar `test_reportes_py312` de la rama de producción. **Es una acción destructiva
   sobre infraestructura de producción y no la ejecuto sin tu permiso explícito**, aunque
   la base sea mía y esté vacía de datos reales.
3. Decidir qué hacer con `test_reportes_dev` en la rama de producción, que es anterior a
   esta sesión.

### D-9 — La función y la base están en regiones distintas

| Componente | Región |
|---|---|
| Función de Vercel | `iad1` (Virginia, us-east-1) |
| Proyecto Neon | `aws-us-east-2` (Ohio) |

Cada consulta cruza de región. Se suma a que `CONN_MAX_AGE = 0` abre una conexión nueva
por request (decisión correcta y deliberada para serverless, ADR-0009): cada petición
paga establecimiento de conexión **más** salto entre regiones.

No es un fallo y no bloquea nada — son decenas de milisegundos, irrelevantes para el uso
en faena. Queda anotado porque es gratis de corregir mientras no haya datos (crear el
proyecto Neon en `us-east-1`) y carísimo después.

### D-10 — Datos de plataforma que conviene tener escritos

- **PostgreSQL 18** en Neon. Django 5.2 lo soporta; nada que hacer.
- **Sin lista blanca de IPs** (`allowed_ips: []`, `block_public_connections: false`): la
  base acepta conexiones desde cualquier origen que tenga credenciales. Es lo normal con
  funciones serverless, cuyas IPs son dinámicas, pero significa que `DATABASE_URL` es la
  única barrera que existe.
- **Límite de 512 MB por rama** (plan gratuito), hoy con ~52 MB usados.
- **Autoescalado 0.25–2 CU**, `suspend_timeout_seconds: 0` (sin suspensión automática).

### Lo que sí quedó confirmado como correcto

| Verificación | Resultado |
|---|---|
| Las 4 variables obligatorias existen en Production | ✅ `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_HTTPS_ONLY` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` en Production y Preview | ✅ |
| `DJANGO_DEBUG` existe **solo** en Development | ✅ producción usa el default `False` |
| `BLOB_READ_WRITE_TOKEN` en los tres entornos | ✅ |
| Preview tiene su juego completo de variables | ✅ |
| Auto-deploy en cada push | ✅ confirmado: 13 previews en 16 h, 1 production |
| Build ejecuta `manage.py collectstatic --noinput` | ✅ visto en el log |
| Producción construyó con Python 3.12 | ✅ (aunque por el camino equivocado — ver D-4) |
| Conteo de estáticos: 141 en producción, 148 en local | ✅ la diferencia son exactamente los 7 archivos nuevos de hoy |
| Build de producción sin errores, 7 s | ✅ |
| **Las 10 migraciones están aplicadas en la base** | ✅ `showmigrations`: todas en `[X]` |
| **No falta ninguna migración por crear** | ✅ `makemigrations --check --dry-run` → "No changes detected", exit 0 |
| Esquema en sincronía con el código a desplegar | ✅ este deploy no necesita `migrate` |
| PostgreSQL 18 en Neon, soportado por Django 5.2 | ✅ |
| Dos ramas Neon, `production` y `dev`, como prevé la spec | ✅ |

## Sistema de deployment propuesto

### Build

`python manage.py collectstatic --noinput`, declarado en `vercel.json`. Sin cambios.

Determinismo: **parcial, y conviene decirlo**. El build es reproducible en cuanto a
comandos, pero `requirements.txt` usa rangos abiertos sin lockfile, así que dos builds
del mismo commit pueden instalar versiones distintas de las dependencias. Prueba
concreta observada hoy: el mismo `requirements.txt` resolvió `psycopg 3.3.5` en Python
3.12 y `3.3.4` en 3.14. Es `SECURITY-REPORT.md` F-07, sigue abierto, y no bloquea este
deploy — pero es la razón por la que "funcionaba ayer" puede dejar de ser cierto sin que
nadie toque código.

### Artifact

No hay artefacto propio: Vercel construye desde el commit y produce una función WSGI
más los estáticos que WhiteNoise sirve desde adentro de esa misma función (ADR-0009,
decisión 5 — Vercel no sirve `/static/` desde `outputDirectory` para este tipo de
proyecto; se confirmó empíricamente).

Trazabilidad: cada deployment de Vercel queda atado a su commit de Git. Es suficiente
para este proyecto y no requiere registro de imágenes ni versionado propio.

**Cambio de peso introducido hoy:** vendorizar las tres librerías de terceros
(`SECURITY-REPORT.md` F-02) movió ~1,6 MB desde CDNs externos hacia el bundle propio.
`heic2any.min.js` solo pesa 1,35 MB (338 KB comprimido). `staticfiles/` total: 4,6 MB,
muy por debajo de cualquier límite de Vercel. El costo es latencia en la primera carga
de la pantalla de adjuntos; la contrapartida es que ya no se ejecuta código de terceros
sin verificar en una pantalla autenticada, y que la app funciona en una primera visita
sin señal. El intercambio ya fue aceptado; queda registrado acá para que nadie lo
descubra por sorpresa.

### Config & Secrets

Sin cambios estructurales. Todo vive en variables de entorno del dashboard de Vercel,
nada en el repositorio (`config/tests/test_deployment_hygiene.py::test_a9` lo verifica).

Obligatorias, fail-loud al arrancar: `DATABASE_URL`, `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_HTTPS_ONLY`.
Opcionales: `DJANGO_DEBUG`, `SENTRY_DSN`, `BLOB_READ_WRITE_TOKEN`,
`DJANGO_CSRF_TRUSTED_ORIGINS`.

**Variable nueva introducida hoy:** `DJANGO_CSP_REPORT_ONLY`.

- **No hace falta configurarla para desplegar.** Su default es `True`, que es el modo
  seguro: la política de seguridad se envía como `Content-Security-Policy-Report-Only`,
  o sea reporta y no bloquea nada. Un deploy sin tocar Vercel se comporta exactamente
  así.
- Ponerla en `False` activa el bloqueo real. Eso es un paso posterior y deliberado, no
  parte de este deploy.
- No es un secreto: es configuración, y puede vivir a la vista.

Se agregó también `.env` y `.env.*` a `.vercelignore` (F-12), para que un
`vercel deploy` desde una laptop no pueda subir el archivo de claves aunque el default
de la CLI cambie.

### Infraestructura

**Sin cambios.** Vercel Hobby + Neon + Vercel Blob, exactamente como está. Este deploy
no provisiona, no modifica y no elimina nada de infraestructura.

La elección ya está justificada en ADR-0009 y no se reabre acá: es un proyecto académico
de un desarrollador solo, donde el costo operativo de un VPS (HTTPS, backups, parches,
monitoreo) fue el criterio decisivo.

### Entornos

| Entorno | Disparador | Base de datos | `DJANGO_HTTPS_ONLY` |
|---|---|---|---|
| Production | push a `main` | rama de producción de Neon | `True` |
| Preview | push a cualquier otra rama | rama **dev** de Neon (compartida, sin branch por preview) | `True` |
| Local | `runserver` | la que tenga el `.env` | `False` |

Entre entornos cambia configuración, nunca código.

**Advertencia real sobre Preview:** los previews comparten la rama dev de Neon. Un
preview que corra migraciones o escriba datos afecta a esa base compartida. Para este
deploy no aplica —no hay migraciones— pero es una trampa para el próximo.

### Estrategia de release

**Hoy, medido y no supuesto: release directo sin ningún control.**

La evidencia está en la propia historia del repo:

```
9c5bf85 chore: trivial commit to trigger Preview deployment (MC-4 check)
5929a5e chore: trigger clean preview redeploy for Blob storage fix
```

Esos commits existen porque un push dispara un deployment solo. La integración Git de
Vercel está activa y `vercel.json` no declara `ignoreCommand`. Es decir: **un merge a
`main` publica en producción de inmediato, sin que nada verifique nada.**

Propuesta para este deploy — **preview primero, promoción después**:

1. Commit del trabajo en la rama actual (`docs/auditoria-y-rescate-specs`).
2. Push. Vercel construye un preview automáticamente.
3. Verificación humana en el preview (checklist en "Verify & Observe").
4. Recién ahí, merge a `main` → producción.

Se descarta canary, blue/green y feature flags: no hay tráfico que justifique el
mecanismo, y Vercel ya da rollback instantáneo, que cubre el mismo riesgo con muchísimo
menos aparato.

### Data & Migrations

**Este deploy no tiene migraciones.** Ningún `models.py` cambió y no hay archivos nuevos
en `*/migrations/`. No hay que correr `migrate` ni antes ni después.

La política general se mantiene (ADR-0009, spec `despliegue-e-infraestructura`,
requisito "Manual, Developer-Triggered Migrations"): las migraciones las aplica una
persona a mano contra Neon, nunca un build step ni un request. `test_a6` lo verifica de
forma ejecutable.

Y lo que hay que tener presente para el próximo deploy que sí traiga esquema: **un
rollback de código NO es un rollback de datos.** Revertir el deployment en Vercel deja
la base con el esquema nuevo. Por eso las migraciones tienen que ser compatibles hacia
atrás (agregar columna nullable antes de usarla; nunca borrar una columna en el mismo
deploy que deja de leerla).

### Deploy gates

**Hoy no existe ninguno.** No hay tests corriendo en CI, no hay bloqueo, no hay revisión
obligatoria. La única barrera es la disciplina de correr `pytest` a mano.

Propuesta, en dos niveles — y son cosas distintas, no dos sabores de lo mismo:

**Nivel 1 — un gate de verdad (recomendado).**
GitHub Actions corre la suite; **solo si pasa** se dispara el deploy.

Requiere tres piezas:
1. Apagar el auto-deploy de Vercel para `main` (Git settings del proyecto, o un
   `ignoreCommand` en `vercel.json` que corte el build cuando no viene de CI).
2. Crear un **Deploy Hook** en Vercel — una URL que dispara un deployment on-demand.
3. Un workflow que corra los tests y, al pasar, haga `curl` al hook.

Costo honesto: la suite tarda ~19 minutos y necesita un **servicio Postgres real** en
CI (los tests no usan SQLite). El plan gratuito de GitHub Actions lo cubre. La URL del
hook es un secreto: va en GitHub Secrets, nunca en el repo.

**Nivel 2 — solo informativo (más simple, pero no es un gate).**
Actions corre los tests y marca la PR en rojo, pero Vercel despliega igual. Sirve para
enterarse, no para impedir. **Lo digo claro porque es el autoengaño más común en esta
etapa: un check rojo y un deploy en vivo pueden coexistir perfectamente.** Si se elige
esta opción, hay que llamarla por su nombre: visibilidad, no control.

Ninguno de los dos niveles es necesario para el deploy de hoy. Los 520 tests ya se
corrieron a mano, en la versión de Python de producción.

### Verify & Observe

Después del deploy, verificación en vivo — **manual, porque no se puede scriptear
honestamente sin una URL desplegada**:

1. `https://<url>/login/` responde 200 con TLS válido, sin cadena de redirecciones.
2. Login real: entra y llega a la pantalla de inicio, sin fallo de CSRF.
3. Un estático nuevo carga: `/static/vendor/dexie.js` responde 200 (prueba que la
   vendorización llegó bien).
4. La consola del navegador **no muestra violaciones de CSP**. Esto es lo que habilita,
   más adelante, pasar `DJANGO_CSP_REPORT_ONLY=False`.
5. Wizard: abrir un paso, guardar un valor, confirmar que persiste.
6. Adjuntos: subir una foto y confirmar que se guarda. Si se tiene una foto con GPS a
   mano, descargarla y confirmar que el EXIF salió (F-05).
7. Generar un `.xlsx` de un reporte cerrado y abrirlo. **Escribir `=1+1` en un campo de
   texto antes de generar y confirmar que en el Excel aparece como texto, no como
   fórmula** (F-01, el arreglo más importante de esta tanda).
8. Cerrar sesión: el botón funciona (bug del selector arreglado).

Observación posterior: Sentry ya está integrado (`DjangoIntegration` +
`send_default_pii=False`). Mirar el proyecto de Sentry las primeras horas.

### Recovery

- **Rollback de código:** en el dashboard de Vercel, promover el deployment anterior a
  producción. Es instantáneo y no requiere rebuild. Es el camino principal.
- **Rollback de datos:** **no aplica en este deploy** — no hay migraciones. Neon tiene
  respaldo automático (ADR-0009) para el caso general.
- **Si la app no arranca:** el modo de falla más probable de esta tanda es el nuevo
  middleware de CSP, que importa `config.storage` y con él `vercel_blob`. Si ese import
  fallara, la app no bootea. Se verificó localmente en Python 3.12 y funciona, pero es
  lo primero a mirar en los logs si algo revienta al arrancar. Rollback inmediato y
  después diagnóstico.
- **Si la CSP rompiera algo:** no puede. Está en `Report-Only`, que por definición no
  bloquea nada. Ese fue el motivo de arrancar así.

## Riesgos específicos de ESTE deploy

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Migraciones inconsistentes | **Nula** | No hay migraciones |
| CSP rompe la app | **Nula** | Report-Only no bloquea |
| El middleware nuevo impide el arranque | Baja | Verificado en 3.12; rollback instantáneo |
| Estáticos nuevos no se sirven | Baja | `collectstatic` verificado: 148 archivos, `vendor/` incluido |
| Deps resuelven distinto que en local | **Media** | Sin lockfile (F-07). Es el riesgo real que queda |
| Primera carga más lenta en adjuntos | Media | Aceptado a cambio de no ejecutar código de terceros sin verificar |

## Detalle menor detectado

`collectstatic` publica `static/vendor/PROVENANCE.md` en
`/static/vendor/PROVENANCE.md`. Es documentación de versiones y hashes, sin secretos.
Expone qué versión de cada librería corre, algo que de todos modos se deduce leyendo los
`.js`. No bloquea nada; si molesta, se mueve fuera de `static/`.

## Autorizaciones pendientes

Ninguna acción se ejecutó. Cada una requiere autorización explícita, en su momento.

### Bloqueantes — decisiones tuyas en el panel de Vercel, no comandos míos

Estas tres no las puedo ni las debo ejecutar yo: cambian la exposición pública del
sistema y el acceso a producción.

- ⬜ **A. Desactivar Deployment Protection en Production** (D-1). Sin esto, desplegar
  publica algo que ningún usuario de faena puede abrir. Recomiendo dejarla activa en
  Preview.
- ⬜ **B. Verificar `DJANGO_ALLOWED_HOSTS` en Production** (D-2). Debe contener el host
  real `proyecto-curso-dmc-gotuzzo.vercel.app`, no `proyecto-curso.vercel.app`, que es
  de otro proyecto. Y `DJANGO_CSRF_TRUSTED_ORIGINS` debe traer el `https://` de ese
  mismo host.
- ⬜ **C. Decidir sobre `SENTRY_DSN`** (D-3). Configurarlo, o aceptar explícitamente que
  producción corre a ciegas. Hoy el backlog dice `DONE` y la realidad dice apagado.
- ⬜ **D. Apuntar el `DATABASE_URL` local a la rama `dev` de Neon** (D-8). Hoy los tests
  se ejecutan contra la rama de producción.
- ⬜ **E. Autorizar (o no) el borrado de `test_reportes_py312`** de la rama de producción
  (D-8). La creé yo hoy; no la borro sin permiso porque toca infraestructura de
  producción.

### Secuencia de despliegue — cada paso se pregunta por separado

1. ⬜ **Commitear** los cambios en la rama actual — reversible.
2. ⬜ **Push** de la rama a GitHub — dispara un deployment de **preview** en Vercel.
3. ⬜ **Verificación humana** en el preview (checklist de "Verify & Observe") — la hacés
   vos, no yo.
4. ⬜ **Merge a `main`** — publica en **PRODUCCIÓN de inmediato** por el auto-deploy
   confirmado. Es el único paso irreversible de la lista.

Los pasos 1 a 3 son seguros aunque A, B y C sigan abiertos: un preview no cambia lo que
ven los usuarios. El paso 4 no debería darse antes de resolver A y B.

### Mejoras posteriores, fuera de este despliegue

5. ⬜ Endurecer `requires-python` a `">=3.12,<3.13"` y corregir el escenario de la spec
   que afirma que el build usa el `.python-version` commiteado (D-4).
6. ⬜ Unificar `pyproject.toml` y `requirements.txt` como fuente de dependencias, y
   apuntar el lockfile de F-07 a la que Vercel realmente lee (D-5).
7. ⬜ Generar el workflow de GitHub Actions con el gate real (deploy hook).
8. ⬜ Pasar `DJANGO_CSP_REPORT_ONLY=False` tras confirmar que la consola está limpia.
9. ⬜ Nota en ADR-0009 sobre el HSTS del borde de Vercel (D-7).

No se pide aprobación en bloque para nada de esto.

## Registro de ejecución y verificación

*(Se completa después de EXECUTE y VERIFY. Vacío a propósito: nada se ejecutó todavía.)*
