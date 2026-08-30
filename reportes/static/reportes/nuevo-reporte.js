/**
 * Client-side `id_local` generation/persistence for the "Nuevo reporte" entry
 * point (change `sincronizacion-numero-registro`, design's D7 — "`id_local`
 * client generation has no host page yet"). Vanilla JS only, no build step
 * (ADR-0001) — Dexie is the sole third-party dependency, loaded via CDN by
 * whichever future template includes this script. The Dexie schema itself
 * lives in `offline-db.js` (D5), which MUST be loaded before this file and
 * exposed as `window.reportesOfflineDB`.
 *
 * IMPORTANT — forward-looking, currently unused (D7): no template in this
 * codebase yet renders a `form[data-nuevo-reporte][data-codigo-tipo]` — the
 * "Nuevo reporte" wizard-entry page is backlog #12's responsibility. This
 * file ships now so #12 can simply add the two `data-*` attributes and a
 * `<script>` tag to its template without any further client-side work.
 * Until #12 lands, the server's `gen_random_uuid()` DB default (D2) is the
 * only `id_local` source, and this script never runs (its `document.
 * querySelector` finds nothing on every existing page). It is verified only
 * via an injected test form in DevTools (tasks.md 4.5) — there is no
 * automated JS test runner in this project (spec's Out of Scope).
 *
 * Depends on the rendered-attribute contract on the entry `<form>` (design's
 * "Data Flow" / "File Changes"): `data-nuevo-reporte` (presence flag) and
 * `data-codigo-tipo` (the `TipoDeReporte.codigo` used as the Dexie `nuevos`
 * primary key).
 */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        var form = document.querySelector("form[data-nuevo-reporte][data-codigo-tipo]");
        if (!form) {
            // No host template includes this hook yet (D7) — no-op, mirrors
            // paso-offline.js's defensive opening pattern.
            return;
        }

        if (typeof Dexie === "undefined") {
            // Dexie failed to load (e.g. offline first visit, CDN
            // unreachable) — id_local generation is unavailable this load;
            // the form still submits without it, and the server's
            // gen_random_uuid() DB default (D2) covers creation.
            return;
        }

        var db = window.reportesOfflineDB;
        if (!db) {
            // offline-db.js failed to load or run before this script — same
            // degrade-to-server-default contract as the Dexie-undefined
            // guard above.
            return;
        }

        var codigoTipo = form.getAttribute("data-codigo-tipo");

        // ---- id_local generation/persistence (design's D7, Data Flow:
        // "crypto.randomUUID() if absent, persisted BEFORE first POST, so
        // every retry reuses it") -------------------------------------------

        function obtenerOCrearIdLocal() {
            return db.nuevos.get(codigoTipo).then(function (fila) {
                if (fila && fila.idLocal) {
                    // Reused across reloads/retries — never regenerated
                    // while the row exists (design's Data Flow diagram).
                    return fila.idLocal;
                }
                var idLocal = crypto.randomUUID();
                return db.nuevos.put({ codigoTipo: codigoTipo, idLocal: idLocal }).then(function () {
                    return idLocal;
                });
            });
        }

        function inyectarCampoOculto(idLocal) {
            var campo = form.querySelector('input[name="id_local"]');
            if (!campo) {
                campo = document.createElement("input");
                campo.type = "hidden";
                campo.name = "id_local";
                form.appendChild(campo);
            }
            campo.value = idLocal;
        }

        // Persist id_local BEFORE the first POST (design's Data Flow) so a
        // retry after a network error/page reload reuses the exact same
        // value instead of generating a second one.
        var idLocalListo = obtenerOCrearIdLocal().then(inyectarCampoOculto);

        // ---- Submit handling (design's Data Flow: "response.redirected ->
        // delete Dexie.nuevos[codigoTipo], location.assign") -----------------

        form.addEventListener("submit", function (evento) {
            evento.preventDefault();
            idLocalListo
                .then(function () {
                    return fetch(form.action, {
                        method: "POST",
                        body: new FormData(form),
                        credentials: "same-origin",
                        redirect: "follow",
                    });
                })
                .then(function (respuesta) {
                    if (respuesta.redirected) {
                        // Success — the report now exists server-side under
                        // this id_local (idempotently, per D3); clear the
                        // pending "nuevos" row so the next "Nuevo reporte"
                        // visit for this codigoTipo generates a fresh UUID.
                        return db.nuevos.delete(codigoTipo).catch(function () {
                            // Deletion failure never blocks navigation.
                        }).then(function () {
                            location.assign(respuesta.url);
                        });
                    }
                    // Non-redirected response (validation error, session
                    // expiry, network-level failure surfaced as a resolved
                    // fetch, etc.) — the id_local row is intentionally kept
                    // so a retry reuses it instead of orphaning a
                    // server-side row under a discarded id_local. No retry
                    // UI is implemented here (out of scope for this PR;
                    // #12 owns the host page's error handling).
                    return null;
                })
                .catch(function () {
                    // Network error — same "keep the row for a future
                    // retry" contract as the non-redirected branch above.
                });
        });
    });
})();
