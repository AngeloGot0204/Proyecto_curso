# ADR 0005: Autenticación con sesiones de Django y sesión tolerante al modo offline

## Estado

Aceptado — la mitad offline nunca se implementó, ver abajo.

## Estado de implementación

Verificado contra el código el 2026-09-01.

**En efecto:** autenticación por sesión de Django (`django.contrib.auth`),
`SESSION_COOKIE_AGE` de 7 días, cuentas creadas por un administrador y sin
auto-registro.

**No se implementó:** la "sesión tolerante" offline. No existe caché de
credenciales ni login sin conexión — autenticarse requiere red. Lo que sí es
tolerante al offline es el trabajo **una vez logueado**: un paso completado sin
señal queda en IndexedDB y, si la sesión expiró al sincronizar, se pide login
de nuevo y el paso guardado se conserva, nunca se descarta.

Queda como trabajo pendiente si el login offline llega a ser un requisito real.

## Contexto

El PRD exige login de usuarios con cuentas creadas por un administrador, sin auto-registro, y dos
roles (administrador y usuario). El DESIGN detalla en S-01 que la pantalla de login debe permitir,
"con sesión previa y sin señal", entrar en modo offline con los datos cacheados, y en S-13 que el
administrador pueda crear usuarios, resetear contraseñas y suspender cuentas.

La ADR-0001 fijó un único proyecto Django que sirve las pantallas, de modo que no existe una
frontera de API pública entre componentes que justifique un esquema de autenticación desacoplado.

Existe además una tensión propia del modo offline: sin conexión no es posible verificar
credenciales contra el servidor, pero la aplicación debe permitir seguir trabajando.

Durante la discusión se incorporó una restricción adicional señalada por el usuario: al tratarse de
una aplicación web, **la misma persona puede trabajar indistintamente desde PC y desde celular**.

## Decisión

Usar el **sistema de sesiones y autenticación integrado de Django** (cookie de sesión), apoyándose
en `django.contrib.auth` para login, cambio y reseteo de contraseña, y en el admin de Django para
la gestión de usuarios y roles.

Para el modo offline se adopta una **sesión tolerante**: si el dispositivo tiene una sesión previa
válida en caché, la aplicación abre y permite trabajar sobre los datos locales sin verificar
credenciales. La validación real de la sesión ocurre **al sincronizar**; si ha expirado, se solicita
iniciar sesión nuevamente y **el borrador local se conserva**, nunca se descarta.

**Duración de la sesión (decisión #10 de RESOLUCION-ADVERSARIAL.md, corrige la contradicción
señalada en la revisión adversarial):** la sesión dura **7 días** (`SESSION_COOKIE_AGE = 604800`),
sin PIN local adicional para reingresar en modo offline. Se prioriza deliberadamente **no bloquear
al usuario en el frente de trabajo** sobre una capa extra de seguridad: el riesgo de que un
dispositivo perdido o sustraído exponga reportes cacheados se considera bajo para este caso de
uso.

Cada dispositivo mantiene su propia sesión, de forma independiente entre PC y celular.

### Revisión de la premisa (2026-09-01)

La justificación original de esa aceptación de riesgo decía que se trata de «reportes de control
de calidad, **sin datos personales sensibles de terceros**». **Esa frase era cierta cuando se
escribió y dejó de serlo.** El backlog #11 (agosto 2026) incorporó adjuntos fotográficos tomados
en faena: una foto de instalación puede contener rostros del personal, patentes de vehículos,
documentación visible en pantalla y metadatos EXIF con geolocalización.

La premisa se corrige acá en lugar de dejarla en pie, porque una decisión apoyada en una
afirmación falsa no está aceptada — está sin revisar. La decisión **se mantiene** (7 días, sin PIN
local), ahora con el costo real a la vista:

- Un dispositivo perdido expone los reportes que ese dispositivo ya había visitado, **incluidas
  las fotos cacheadas**, mientras la sesión siga vigente. Sin señal no hay forma de validar la
  sesión, así que el service worker sirve el HTML cacheado sin poder consultar al servidor
  (`SECURITY-REPORT.md` F-10).
- Se asume que los dispositivos de faena tienen bloqueo de pantalla y cifrado del sistema
  operativo. **Si esa suposición no se cumple, esta decisión debe reabrirse**: es la única capa
  que queda entre un teléfono perdido y los reportes.

Mitigación aplicada en su momento (`SECURITY-REPORT.md` F-05, opción 1), que reduce el daño sin
cambiar esta decisión: los metadatos EXIF —geolocalización incluida— se eliminan al subir cada
adjunto, y los archivos se borran del almacenamiento cuando se elimina un reporte. Límite conocido:
un HEIC sin convertir no se puede decodificar con el Pillow instalado y conserva su GPS.

Lo que esta revisión **no** resuelve: las URLs de los adjuntos siguen siendo públicas, permanentes
y no revocables. Eso es `SECURITY-REPORT.md` F-05, que sigue abierto y requiere una decisión
propia.

## Alternativas consideradas

- **Autenticación por token (JWT)** — es el enfoque habitual cuando el frontend está desacoplado
  del backend y habría facilitado una futura app nativa. Se descartó porque, con un único
  despliegue Django (ADR-0001), no aporta ninguna capacidad adicional y sí introduce trabajo
  propio: gestión de expiración, renovación del token y decisión sobre dónde almacenarlo en el
  cliente, con sus riesgos asociados. Las sesiones de Django cubren el caso sin código adicional.

- **Exigir conexión para iniciar sesión siempre, sin sesión offline** — sería más seguro y
  notablemente más simple de razonar. Se descartó porque contradice de forma directa el requisito
  de S-01 en el DESIGN y anularía el propósito del modo offline: el usuario que llega al frente de
  trabajo sin señal no podría siquiera abrir la aplicación.

## Consecuencias

- Login, reseteo de contraseña, permisos y gestión de usuarios provienen de Django sin desarrollo
  propio, reforzando la elección de la ADR-0001.
- El administrador gestiona cuentas desde el admin de Django, cubriendo S-13 con muy poco código.
- El usuario puede trabajar sin señal y no pierde su borrador aunque la sesión haya expirado
  mientras estaba desconectado.
- **Consecuencia sobre el uso multi-dispositivo (PC y celular):** el borrador local reside en el
  almacenamiento del navegador de **un dispositivo concreto** (ADR-0004). En consecuencia, un
  reporte **no sincronizado existe únicamente en el dispositivo donde se capturó** y no aparece en
  los demás; una vez sincronizado, queda disponible desde cualquier dispositivo. La regla es:
  **sin sincronizar, sólo en ese dispositivo; sincronizado, en todos.** Esto no es un defecto a
  corregir sino la naturaleza del almacenamiento offline, pero debe comunicarse de forma
  explícita en la interfaz para que el usuario no interprete que perdió el reporte. Se registra
  como ajuste pendiente del DESIGN que el chip `local` de S-02 y S-15 exprese "solo en este
  dispositivo".
- **Costo real:** si un dispositivo desbloqueado se pierde o es sustraído, los reportes cacheados
  quedan accesibles sin solicitar contraseña durante la ventana de 7 días de la sesión, sin PIN
  local que la acote más. Es el precio inherente de permitir trabajo offline y de la decisión
  consciente de priorizar no bloquear al usuario en campo; no se elimina, sólo se acota a 7 días.
- **Costo real:** la sesión basada en cookie es adecuada para navegador, pero si en el futuro se
  incorpora una app nativa habrá que añadir un esquema por token junto a Django REST Framework,
  tal como anticipa la ADR-0001.
