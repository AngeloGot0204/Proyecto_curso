# ADR 0001: Aplicación Django monolítica con capa offline mínima en JavaScript

## Estado

Aceptado

## Contexto

El PRD exige una app web responsiva (escritorio y móvil/tablet) que permita completar reportes de
control de calidad **sin conexión** en campo y sincronizarlos al recuperar internet, con login de
usuarios administrados por un administrador, y que genere un archivo `.xlsx` idéntico en formato
al reporte de referencia.

El DESIGN define 15 pantallas, de las cuales 5 son de escritorio (revisión previa, admin de
usuarios, admin de tipos de reporte) y el resto móviles.

Restricción determinante del equipo: el proyecto lo desarrolla una sola persona, cuya experiencia
de programación es principalmente **Python** y limitada fuera de eso. Esta restricción no es un
detalle de preferencia: descarta arquitecturas que exijan dominar en paralelo un segundo
ecosistema completo.

Existe una tensión real entre esas dos fuerzas: el modo offline es, por definición, un problema
del navegador y no puede resolverse solo con Python — ningún framework de servidor lo evita.

## Decisión

Construir un **único proyecto Django (Python)** que sirve las pantallas, gestiona autenticación y
roles, persiste los reportes y genera el `.xlsx`; complementado por una **capa offline propia y
acotada en JavaScript vanilla** (service worker, almacenamiento local del borrador y cola de
subida), sin frameworks de frontend ni build pipeline.

Reparto aproximado: ~85% Python, ~15% JavaScript.

**Sobre el wizard (aclaración, decisión #1 de RESOLUCION-ADVERSARIAL.md):** el servidor Django lee
la definición declarativa del tipo de reporte (ADR-0003) y **renderiza el formulario completo del
wizard ya en HTML**, no envía una definición YAML/JSON para que el celular la interprete y arme el
formulario por su cuenta. Esa página HTML servida por Django es la que el service worker cachea
para uso offline (ADR-0004). La validación fuerte de los campos (obligatoriedad, formato, rangos)
ocurre **al sincronizar, en el servidor**; sin conexión el navegador sólo guarda lo que el usuario
escribe, sin validar contra la definición.

## Alternativas consideradas

- **Django sin modo offline en el MVP (formularios servidos, HTMX)** — era viable y de lejos la
  opción más rápida de construir para un desarrollador Python en solitario (~98% Python), y
  cubría todas las demás exigencias del PRD. Se descartó porque **agregar offline más adelante no
  sería agregar una función, sino rehacer la capa de formulario**: un formulario servido por el
  servidor asume conexión en cada paso, de modo que introducir offline obligaría a reescribir esa
  capa en JavaScript de todos modos, pero ya con reportes reales y usuarios en producción. Barato
  hoy, caro después.

- **API Python separada (FastAPI o Django REST) + frontend SPA en React/Vue como PWA** — es la
  arquitectura más sólida para offline y la más alineada con la práctica habitual de la industria.
  Se descartó por desproporción respecto al equipo y al problema: obliga a aprender el ecosistema
  JavaScript completo además de Python, mantener dos proyectos y un contrato de API, y
  **construir a mano el panel de administración** que Django ya provee. El beneficio adicional
  sobre la opción elegida no lo requiere este proyecto.

## Consecuencias

- El desarrollador trabaja en su lenguaje conocido para la lógica de negocio, el modelo de datos,
  la autenticación y la generación del Excel (openpyxl es Python).
- El `django.contrib.admin` cubre buena parte de las pantallas S-13 (admin de usuarios) y S-14
  (admin de tipos de reporte) con muy poco código propio.
- Un solo despliegue y una sola base de código: sin contrato de API que versionar ni sincronizar
  entre dos proyectos.
- Sin build pipeline de frontend (npm, bundler): menos herramientas que mantener y menos
  superficie de fallo para un desarrollador en solitario.
- La capa offline existe desde el primer día, de modo que las funcionalidades futuras se apoyan
  sobre ella en lugar de forzar su reescritura.
- Camino de crecimiento abierto: si en el futuro se requiere una app nativa, se suma Django REST
  Framework sobre el mismo modelo de datos — es aditivo, no una reescritura.
- **Costo real:** hay que escribir y depurar JavaScript propio sí o sí. La capa offline (service
  worker, borradores locales, cola de subida idempotente) será la parte técnicamente más difícil
  del proyecto y la más alejada de la experiencia actual del desarrollador. Es una dificultad
  concentrada al inicio, asumida deliberadamente para evitar una migración posterior más costosa.
- **Costo real:** al no usar un framework de frontend, comportamientos de UI que el DESIGN pide
  (wizard de 5 pasos con navegación libre, cálculo de Δ en vivo, chips de estado reactivos) se
  implementan a mano en JavaScript vanilla, lo que es más verboso y más propenso a errores que
  con React o Vue.
- **Costo real:** el renderizado y la capa offline conviven en el mismo proyecto, así que la
  disciplina para no mezclar responsabilidades queda a cargo del desarrollador, sin la separación
  que impondría una frontera de API.
