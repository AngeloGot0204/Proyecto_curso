---
title: "Design 2 — Mockup de alta fidelidad · Generador de Reportes de Campo"
version: "mockup v1"
fuente: "uploads/DESIGN.md · Mockup Reportes de Campo.dc.html"
---

# DESIGN2 — Especificación visual del mockup

Continuación de `uploads/DESIGN.md`. Ese documento define pantallas, estados y reglas;
este define **cómo se ven y se miden** en el mockup `Mockup Reportes de Campo.dc.html`.
No repite el inventario ni las reglas de validación: ver DESIGN.md secciones 3, 7 y 8.

## 1. Lenguaje visual

Industrial/técnico, alto contraste para uso a pleno sol. Sin sombras decorativas dentro de
las pantallas, sin esquinas redondeadas, sin degradados (salvo el velo del botón fijo de
S-02). El color solo sirve para dos cosas: jerarquía (negro) y advertencia (ámbar).

| Token | Valor | Uso |
|---|---|---|
| Fondo de app | `#f4f3f1` | Lienzo de todas las pantallas |
| Superficie | `#ffffff` | Tarjetas, campos, barras, tablas |
| Tinta | `#14130f` | Texto principal, botón primario, chips activos, bordes de foco |
| Tinta secundaria | `#4a463f` | Texto de apoyo, etiquetas de rol |
| Tinta mono | `#6f6a61` | Líneas monoespaciadas, metadatos |
| Línea | `#d9d5cf` | Bordes de campo y tarjeta |
| Línea interna | `#eeece8` | Separadores dentro de una tarjeta o tabla |
| Deshabilitado | fondo `#d9d5cf` · texto `#8b867d` | Primario bloqueado |
| Ámbar borde | `#b06a00` / `#e0bd7c` | Advertencia, "No cumple", `falló 2v` |
| Ámbar fondo | `#fdf1dc` | Tarjeta de aviso ámbar |
| Ámbar texto | `#7a5a1c` | Línea mono dentro de tarjeta ámbar |

Ningún otro color. El ámbar nunca se usa para énfasis positivo.

## 2. Tipografía

- **UI:** Helvetica Neue / Helvetica / Arial. 26 px título de login · 22 px título escritorio ·
  19 px título de pantalla móvil · 17 px encabezado de wizard · 15–16 px valor de campo ·
  14 px texto de tarjeta · 13 px etiqueta de campo (600).
- **Mono:** IBM Plex Mono 400/500. 12 px indicador de paso · 11 px metadatos, autoría, ayuda de
  campo y razón de bloqueo · 10 px chips y encabezados de tabla (mayúsculas, `letter-spacing`
  0.06–0.12em).
- Regla: **todo dato de sistema es mono** (N° de registro, horas, códigos, tamaños de archivo,
  quién editó y cuándo). Todo lo que el usuario escribe o lee como prosa es sans.
- Mínimos: nunca menos de 13 px para texto que el usuario debe leer en terreno; 10–11 px queda
  reservado a chips y metadatos redundantes.

## 3. Grilla y medidas

- Frame móvil: **390 × 844**. Frame escritorio (S-14): **1120 × 844**.
- Padding de contenido móvil: 16 px lateral; listas de tarjetas 12 px para ganar ancho de tarjeta.
- Gap vertical: 8 px dentro de un grupo · 12–16 px entre campos · 18–20 px entre bloques.
- Objetivos táctiles: campos 46–50 px · botones 44–52 px · casillas Sí/No 48 × 44 · filas de
  tabla y de participante ≥ 48 px.
- Barras de acción fijas: 68 px de alto real; el scroll lleva `padding-bottom` 96–104 px para que
  nada quede debajo.
- Escritorio S-14: sidebar 232 px · grilla de contenido `316px minmax(0,1fr)` con gap 28 px ·
  tabla de secciones `minmax(0,1fr) 48px 152px`.

## 4. Componentes (implementación)

**Barra de pantalla.** Superficie blanca, borde inferior `#d9d5cf`, padding 12/16.
Orden fijo: volver (←, 24 px) · título · indicador `n/5` mono · chip de conexión · avatar 32 px.
En S-02 (raíz) no hay volver.

**Indicador de pasos.** Cinco cuadrados: activo 12 px sólido, completado 8 px sólido,
pendiente 8 px con borde `#d9d5cf`. A la derecha de la misma fila, `guardado local ✓` en mono 11 px.

**Campo.** Etiqueta 13/600 arriba · caja blanca 46 px con borde 1 px · ayuda mono 11 px debajo.
Valor numérico/código/hora en mono. Error: borde 2 px `#14130f` + mensaje 13/600 debajo
(qué pasó + qué hacer). El rojo no existe en la paleta: el error se marca por peso de borde.

**Checklist por rol (móvil).** Una tarjeta por ítem: número mono + enunciado, luego una fila por
rol con el par Sí/No a la derecha. Marcado = negro sólido; sin completar = borde punteado
`#a8a29a`. Pie mono con autoría por rol. Un "No cumple" sube el borde de la tarjeta a 2 px ámbar,
inserta tarjeta ámbar y abre la observación (borde negro = requerida).

**Chip de estado.** Mono 10 px mayúsculas, padding 3–4 / 5–6 px, sin radio.
Tres pesos: negro sólido (`completo`, `falló 2v` en ámbar sólido), borde negro (`mi turno`,
`local`, `offline`), borde gris (`pend. otra parte`, `borrador`, `pendiente`).

**Tarjeta de aviso.** Neutra: superficie blanca, borde `#d9d5cf`, texto 13 px. Ámbar: fondo
`#fdf1dc`, borde `#e0bd7c`, título 14/600 + explicación 13 px.

**Barra de acciones.** Secundario a la izquierda (borde negro, relleno negro al hover), primario a
la derecha. El primario deshabilitado **siempre** lleva la razón en mono 10 px debajo, alineada a
la derecha ("falta 1 campo obligatorio", "corregí los 3 errores primero", "faltan las secciones 4 y 5",
"sin señal · se reintenta solo al reconectar").

**Hoja modal (S-09).** Velo `rgba(20,19,15,0.5)` sobre la pantalla anterior atenuada, hoja anclada
abajo con borde superior 2 px negro, tirador 44 × 4, encabezado blanco con conteo mono, cuerpo con
scroll y barra de acciones propia. Errores en tarjeta de borde negro con `→` por fila (enlace al
campo); advertencias en tarjeta ámbar sin acción.

## 5. Estados representados en el mockup

| Pantalla | Estado elegido | Por qué |
|---|---|---|
| S-01 | Sin señal, sesión cacheada | El caso más frecuente en terreno |
| S-02 | Cola de 3 + un reporte `completo` sin visto bueno | Muestra banner y el destaque de DESIGN.md §7 |
| S-04 | Un campo obligatorio vacío | Error inline + primario bloqueado con razón |
| S-05 | Ítem 02 en "No cumple", ítem 03 sin QA | Advertencia que no bloquea + celda vacía por rol |
| S-09 | 3 errores / 2 advertencias | Las dos listas separadas y la generación bloqueada |
| S-10 | `pend. otra parte`, secciones 4–5 abiertas | Visto bueno deshabilitado con motivo |
| S-14 | Tipo activo con logo cargado | Reemplazo de logo + secciones de solo lectura |
| S-15 | 2 `local` + 1 `falló 2v` | Reintento manual y regla de no duplicar |
| S-06 | Ítem 03 con término anterior al inicio | Único error bloqueante del paso; ítem 04 sin registrar |
| S-08 | QA Antamina sin completar, 1,8 MB sin subir | Handoff pendiente + adjuntos que no bloquean |

Los tres estados alternables desde Tweaks: conexión (`offline` / `en línea`), banner de cola de
subida en S-02, error de campo obligatorio en S-04.

## 6. Copy

Español neutro, voseo en imperativo ("Revisá", "Reintentá", "Solicitá tu cuenta"), vocabulario del
formato original (frente, turno, tipo de roca, pull test, taladro, resina, perno helicoidal).
Sin emoji. Formato de error: **qué pasó + qué hacer** en una sola oración corta.
Los metadatos mono van en minúscula y sin punto final.

## 6.b Patrones propios de S-06 y S-08

**Fila de horas (S-06).** Tres campos en una fila: Inicio · Término · `Δ min` (78 px, mono).
Δ se ingresa a mano y queda vacío (`—`) mientras las horas sean inconsistentes. Hora sin
registrar se muestra como `--:--` en gris con ayuda "tocá para usar la hora actual".
Término anterior al inicio es el **único error bloqueante** del paso: borde 2 px en la tarjeta y en
el campo culpable, mensaje 13/600, y razón en la barra de acciones ("corregí la hora del ítem 03").

**Adjuntos (S-08).** Grilla de 2 columnas: miniatura 104 px + nombre, peso y `local` en mono;
la celda de agregar es un recuadro punteado negro de 152 px con `+`, rótulo y límites
(máx. 5 · 5 MB c/u). El peso sin subir se comunica con tarjeta ámbar que aclara explícitamente
que **no bloquea** generar el documento.

## 7. Pendiente

- Pantallas no dibujadas por derivarse de las existentes: S-03 (lista de tipos, reusa la tarjeta de
  S-02 con estado "próximamente"), S-07 (misma fila de horas de S-06 + rango esperado como el de
  S-09), S-13 (misma tabla y sidebar de S-14).
- Layout de escritorio del wizard S-04→S-08 (DESIGN.md §10).
- Logo institucional real para S-01 y logo de cliente real para S-14: hoy son placeholders.
- Definir tipografía mono definitiva si el equipo prefiere una licenciada distinta a IBM Plex Mono.
