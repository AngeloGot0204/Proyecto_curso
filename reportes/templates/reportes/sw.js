{% load static %}
/*
 * Minimal hand-written service worker (change `capa-offline`; design's
 * Decision "Hand-written sw.js, not Workbox" and "sw.js served as a Django
 * template"). Rendered via the static template tag so asset URLs stay
 * authoritative across dev/production — never write the Django comment
 * token `{#` in this file. Caches only the currently-rendered wizard step's
 * own HTML response plus its static assets; GET-only; version bump via
 * CACHE below.
 */

var CACHE = "reportes-offline-v1";

self.addEventListener("install", function (evento) {
  self.skipWaiting();
});

self.addEventListener("activate", function (evento) {
  evento.waitUntil(
    caches
      .keys()
      .then(function (nombres) {
        return Promise.all(
          nombres
            .filter(function (nombre) {
              return nombre !== CACHE;
            })
            .map(function (nombre) {
              return caches.delete(nombre);
            })
        );
      })
      .then(function () {
        return self.clients.claim();
      })
  );
});

self.addEventListener("fetch", function (evento) {
  var solicitud = evento.request;

  // Cache API only stores GET; never intercept POST/PUT/etc. (design's
  // "GET only" row — cache.put rejects for non-GET requests).
  if (solicitud.method !== "GET") {
    return;
  }

  var url = new URL(solicitud.url);

  // Multi-user device hygiene: navigating to /login/ purges the cached HTML.
  if (url.pathname === "/login/") {
    evento.waitUntil(
      caches.open(CACHE).then(function (cache) {
        return cache.keys().then(function (claves) {
          return Promise.all(
            claves
              .filter(function (clave) {
                var claveUrl = new URL(clave.url);
                return claveUrl.origin === self.location.origin && !claveUrl.pathname.startsWith("/static/");
              })
              .map(function (clave) {
                return cache.delete(clave);
              })
          );
        });
      })
    );
    return;
  }

  var esNavegacionDePaso = solicitud.mode === "navigate" && /\/reportes\/\d+\/paso\/[^/]+\/?$/.test(url.pathname);
  var esEstatico = url.pathname.indexOf("/static/") === 0 || url.origin !== self.location.origin;

  // Last-resort fallback: the Fetch API requires event.respondWith() to
  // resolve to a Response, never `undefined` — returning `undefined` (e.g.
  // from an empty cache.match()) throws "Failed to convert value to
  // 'Response'" inside the worker and surfaces as a hard network error even
  // when the underlying failure was benign (a stale/never-cached URL, a
  // transient hiccup). Every branch below must end in a real Response.
  function respuestaDeReserva() {
    return new Response("Sin conexión.", {
      status: 503,
      statusText: "Offline",
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  if (esNavegacionDePaso) {
    // Network-first: server data is authoritative; stale HTML must never
    // win while online. Cache the response only when it is a genuine,
    // non-redirected, same-origin success — never opaque/error responses.
    evento.respondWith(
      fetch(solicitud)
        .then(function (respuesta) {
          if (respuesta.ok && respuesta.type === "basic" && !respuesta.redirected) {
            var copia = respuesta.clone();
            caches.open(CACHE).then(function (cache) {
              cache.put(solicitud, copia);
            });
          }
          return respuesta;
        })
        .catch(function () {
          return caches.match(solicitud).then(function (respuestaCacheada) {
            return respuestaCacheada || respuestaDeReserva();
          });
        })
    );
    return;
  }

  if (esEstatico) {
    // Cache-first: fast, offline-safe; freshness comes from bumping CACHE.
    evento.respondWith(
      caches.match(solicitud).then(function (respuestaCacheada) {
        if (respuestaCacheada) {
          return respuestaCacheada;
        }
        return fetch(solicitud)
          .then(function (respuesta) {
            if (respuesta.ok) {
              var copia = respuesta.clone();
              caches.open(CACHE).then(function (cache) {
                cache.put(solicitud, copia);
              });
            }
            return respuesta;
          })
          .catch(function () {
            return respuestaDeReserva();
          });
      })
    );
    return;
  }

  // Anything else (admin, media, unrelated routes): pass through, out of
  // scope for this offline slice.
});

/* This file references {% static 'reportes/paso.js' %} so the /sw.js
 * response body proves it was rendered via the Django template engine, not
 * served as a raw static file (design's Decision + Testing Strategy). It is
 * not otherwise used at runtime by the service worker itself. */
