# Generador de Reportes de Campo

Aplicación web para completar reportes de calidad en campo y generar el
`.xlsx` final sobre la plantilla original de la empresa, sin abrir Excel ni
ajustar formato a mano.

Está pensada para trabajo en terreno: el formulario se completa paso a paso,
funciona sin señal y sincroniza cuando vuelve la conexión.

| | |
|---|---|
| **Aplicación** | https://proyecto-curso-dmc-gotuzzo.vercel.app/ |
| **Video demostrativo** | https://www.youtube.com/watch?v=TFGSEiEMd2Y |
| **Acceso de prueba** | `admin` / `admin123` |

El sistema arranca sin tipos de reporte cargados: el primer paso es subir una
plantilla `.xlsx` y su definición YAML desde la administración.

## Cómo funciona, en una pasada

Un **tipo de reporte** no se programa: se configura. Cada uno se define en un
archivo YAML declarativo que dice qué secciones y campos tiene, y a qué celda
del `.xlsx` va cada valor. Agregar un tipo nuevo no toca código.

El flujo de un reporte:

```
Nuevo reporte → wizard paso a paso → revisión → visto bueno → generar .xlsx
```

El visto bueno lo da únicamente quien creó el reporte, y es lo que habilita la
generación: completar todos los campos no alcanza. Se puede invitar a otros
usuarios a colaborar; todos editan cualquier sección y cada cambio queda
registrado con autor y fecha.

## Stack

- **Django 5.2** sobre **Python 3.12**, server-rendered, sin framework de frontend
- **PostgreSQL** (Neon en producción)
- **openpyxl** para escribir sobre la plantilla `.xlsx` original
- **JavaScript vanilla**, sin build step — IndexedDB (Dexie) y un service
  worker escrito a mano para la capa offline
- **Vercel** para el despliegue, **Vercel Blob** para archivos, **Sentry** para
  errores

## Levantar el proyecto

Necesitás **Python 3.12** y una base PostgreSQL accesible.

La versión está fijada en `.python-version`. Vercel despliega con esa misma
versión, así que desarrollar en otra abre la puerta a que algo funcione en tu
máquina y falle en producción. Django 5.2 soporta de 3.10 a 3.14, pero lo que
corre en producción hoy es 3.12.

```bash
# 1. Entorno virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env             # y completá los valores

# 4. Base de datos
python manage.py migrate

# 5. Primer usuario administrador
python manage.py createsuperuser

# 6. Servidor
python manage.py runserver
```

Entrás por `http://localhost:8000/`.

### Variables de entorno

Cuatro son obligatorias y la app **falla al arrancar** si falta alguna, a
propósito: es preferible un error explícito a un default silencioso en
producción.

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Conexión PostgreSQL |
| `DJANGO_SECRET_KEY` | Clave de firma de Django |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `DJANGO_HTTPS_ONLY` | Endurecimiento de transporte. Acepta **exactamente** `True` o `False` — `true`, `1` o `yes` son rechazados, para que un typo no desactive las protecciones en producción sin que nadie lo note |

Las opcionales (`DJANGO_DEBUG`, `SENTRY_DSN`, `BLOB_READ_WRITE_TOKEN`,
`DJANGO_CSRF_TRUSTED_ORIGINS`) están descritas en `.env.example`.

## Tests

```bash
pytest                                    # todo
pytest reportes/tests/test_views.py       # un archivo
pytest -k "cerrar or chip"                # por nombre
```

La suite usa `--reuse-db`: la primera corrida crea la base de test y las
siguientes la reutilizan. Si cambiaste migraciones y algo no cuadra, agregá
`--create-db`.

La suite completa tarda varios minutos. Para iterar, filtrá por archivo o con
`-k`.

## Cómo está organizado

```
config/          Settings, URLs raíz, storage backend de Vercel Blob
usuarios/        Usuario custom, roles, autenticación, admin de cuentas
tipos_reporte/   Motor de definiciones YAML, validador, generador de Excel
reportes/        Wizard de captura, validación, cierre, adjuntos, offline
templates/       base.html, sidebar, partials compartidos
static/          tokens.css, components.css, JS compartido
openspec/        Specs vivas y ciclos SDD archivados
adrs/            Decisiones de arquitectura (formato MADR)
```

### El motor de definiciones

`tipos_reporte` es el corazón del proyecto. Cuando un administrador activa una
definición YAML, un validador la revisa **entera** antes de aceptarla y acumula
todos los problemas en una sola pasada, en vez de cortar en el primer error.
Verifica que los tipos de dato existan, que las celdas tengan notación válida,
que no haya dos campos apuntando a la misma celda y que cada celda destino sea
ancla de su rango combinado — escribir en una celda no-ancla revienta en
openpyxl.

Si algo falla, el tipo de reporte queda exactamente como estaba.

### La capa offline

Cada paso del wizard se guarda en IndexedDB apenas se escribe, así que
retroceder o cerrar la app no pierde nada. Si no hay señal al enviar, el paso
queda en cola y la pantalla de sincronización (S-15) lista todo lo pendiente
entre reportes, con reintento por fila.

El reporte en sí **se crea online**: necesita conexión para existir y recibir
su número de registro. Lo que funciona sin señal es completarlo.

## Documentación

| Documento | Qué responde |
|---|---|
| `PRD.md` | Qué problema resuelve y para quién |
| `DESIGN.md` / `DESIGN2.md` | Pantallas y sistema visual |
| `TECH-DESIGN.md` | Arquitectura y modelo de datos |
| `adrs/` | Por qué se decidió cada cosa, y qué se descartó |
| `BACKLOG.md` | Los 15 ítems del proyecto y su estado |
| `REVISION-ADVERSARIAL.md` | Crítica del propio diseño; `RESOLUCION-ADVERSARIAL.md` resuelve sus 15 puntos |
| `openspec/specs/` | Contrato vigente de cada capacidad |
| `openspec/changes/archive/` | Ciclo SDD completo de cada cambio |
| `SECURITY-REPORT.md` | Auditoría de seguridad: 14 hallazgos con evidencia y estado |
| `DEPLOY-PLAN.md` | Sistema de despliegue y 13 hallazgos verificados sobre la infraestructura |
| `CLAUDE.md` | Contexto del proyecto para el agente: convenciones y trampas conocidas |

Si vas a tocar código, `openspec/specs/` es lo que describe el comportamiento
esperado hoy. Los `adrs/` explican por qué las cosas son como son.

## Skills instaladas

`.agents/skills/` trae cuatro skills **de terceros** usadas durante el desarrollo.
Ninguna fue escrita en este repositorio; `skills-lock.json` registra el origen y el
hash de cada una.

| Skill | Origen | Qué produjo acá |
|---|---|---|
| `generar-backlog` | `adminoryslabs/Skills` | `BACKLOG.md` |
| `revision-adversarial` | `adminoryslabs/Skills` | `REVISION-ADVERSARIAL.md` |
| `security-pass` | `adminoryslabs/Armory` | `SECURITY-REPORT.md` |
| `deploy-pass` | `adminoryslabs/Armory` | `DEPLOY-PLAN.md` |

```bash
npx skills add adminoryslabs/Skills --skill generar-backlog
```

## Integración continua

`.github/workflows/ci.yml` corre en cada push y en cada pull request: la suite
completa (520 pruebas) contra PostgreSQL real en Python 3.12, más `check --deploy`,
verificación de migraciones pendientes y comprobación SHA-256 de las librerías
vendorizadas en `static/vendor/`.

## Despliegue

Vercel construye con `python manage.py collectstatic --noinput` y sirve la app
como función WSGI. Los estáticos los sirve WhiteNoise desde adentro de la
función, no el CDN de Vercel.

Las migraciones **no** corren solas: se aplican a mano contra la base de
producción antes de depender del esquema nuevo.

```bash
python manage.py migrate
```
