# ADR 0009: Despliegue en Vercel, base de datos en Neon y almacenamiento en Vercel Blob

## Estado

Aceptado

## Contexto

Ninguna ADR anterior fijaba dónde y cómo se despliega la aplicación, ni dónde viven la base de
datos y los archivos (plantillas `.xlsx`, logos, adjuntos, Excel generados) — hallazgo #8 de la
revisión adversarial (`REVISION-ADVERSARIAL.md`).

El proyecto es **académico, sin fines comerciales**, desarrollado y mantenido por una sola
persona (restricción ya fijada en la ADR-0001). Esto pesa sobre la elección: no hay presupuesto de
infraestructura ni tiempo para operar servidores propios, y los planes gratuitos de los
proveedores de nube dejan de aplicar sin restricción en cuanto el uso es comercial — algo que aquí
no ocurre.

Dos requisitos técnicos previos condicionan la elección:

1. El service worker de la ADR-0004 **exige HTTPS** para registrarse (salvo en `localhost`), de
   modo que el hosting elegido tiene que resolver certificados y HTTPS sin trabajo manual.
2. La ADR-0005 fija sesiones de Django con cookies; conviene una base de datos PostgreSQL gestionada
   con respaldo automático, dado que no hay a nadie dedicado a administrar backups a mano.

## Decisión

Desplegar en **Vercel** (hosting, HTTPS automático por certificado gestionado), con **Neon**
como base de datos **PostgreSQL** (con respaldo automático) y **Vercel Blob** como almacenamiento
de archivos: logos de `TipoDeReporte`, plantillas `.xlsx` y los Excel generados y adjuntos que
requieran persistencia (ver ADR-0004, decisión sobre adjuntos).

Al tratarse de un proyecto académico sin fines comerciales, el **plan gratuito (Hobby) de Vercel**
aplica sin la restricción de sus términos de uso para proyectos comerciales, cubriendo el
despliegue sin costo.

El service worker (ADR-0004) requiere HTTPS para registrarse; Vercel lo resuelve automáticamente
para cada despliegue, sin certificados que gestionar a mano.

## Alternativas consideradas

- **Servidor propio (VPS) con Nginx, Gunicorn y PostgreSQL autogestionado** — daría control total
  y ningún límite de plan gratuito. Se descartó por el costo operativo: hay que configurar HTTPS
  (Let's Encrypt y su renovación), backups de base de datos, actualizaciones del sistema operativo
  y monitoreo de disponibilidad — todo trabajo adicional para un desarrollador en solitario que ya
  asumió, en la ADR-0001, construir la capa offline como su mayor riesgo de cronograma.

- **Heroku (o equivalente) con Postgres add-on** — es una opción PaaS comparable a Vercel, con
  despliegue simple y HTTPS automático. Se descartó por no ofrecer, para este caso, ventajas claras
  sobre Vercel + Neon, y por la mayor incertidumbre reciente sobre la vigencia de sus planes
  gratuitos frente a la oferta actual de Vercel/Neon.

- **Firebase / Supabase como backend gestionado completo** — habría cubierto base de datos,
  autenticación y almacenamiento en una sola plataforma. Se descartó porque la aplicación ya está
  construida sobre Django (ADR-0001) con su propio sistema de autenticación (ADR-0005) y ORM;
  adoptar otro backend gestionado duplicaría esas piezas en lugar de completarlas.

## Consecuencias

- El desarrollador no administra servidores, certificados HTTPS ni backups de base de datos: los
  tres quedan cubiertos por los proveedores elegidos.
- El service worker (requisito de la ADR-0004) funciona sin configuración adicional de HTTPS.
- Los archivos (logos, plantillas, generados, adjuntos) quedan fuera del sistema de archivos del
  servidor de aplicación, coherente con un entorno de despliegue de Vercel que no garantiza
  almacenamiento persistente en disco entre despliegues.
- **Costo real:** el proyecto queda atado a tres servicios externos (Vercel, Neon, Vercel Blob).
  Si el plan gratuito no alcanzara en el futuro (más tráfico, más almacenamiento), habría que
  evaluar planes pagos o migrar, con el trabajo de portabilidad que eso implique.
- **Costo real:** al ser un proyecto académico sin fines comerciales, el uso del plan Hobby de
  Vercel es válido hoy; si el proyecto cambiara de naturaleza (uso comercial), habría que revisar
  los términos de servicio y probablemente migrar de plan.
- **Costo real:** Neon y Vercel Blob introducen límites propios de cuota (almacenamiento, ancho de
  banda, cómputo) en sus planes gratuitos, que no fueron medidos contra el volumen esperado de
  reportes y adjuntos; conviene revisarlos antes de un uso intensivo en campo.
