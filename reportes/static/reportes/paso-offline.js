/**
 * Client-side offline draft layer for the `paso` wizard step (changes
 * `capa-offline` and `sincronizacion-numero-registro`; design's "Technical
 * Approach", "Data Flow", "Interfaces / Contracts"). Vanilla JS only,
 * hand-rolled debounce, no build step (ADR-0001) — Dexie is the sole
 * third-party dependency, loaded via CDN in `paso.html`. The Dexie schema
 * itself lives in `offline-db.js` (D5), loaded before this file and exposed
 * as `window.reportesOfflineDB`. No JS test runner exists in this project
 * (spec's Out of Scope); coverage is the manual DevTools script in
 * tasks.md Phase 4.
 *
 * Depends on the rendered-attribute contract on the step `<form>`:
 * `data-reporte-id`, `data-seccion-id`, `data-servidor-actualizado`
 * (design's File Changes / Interfaces sections).
 *
 * Submission uses `fetch()` instead of `form.submit()` (design's D4), so
 * outcome can be observed and reflected as `pendiente`/`fallo` draft states
 * with an inline, manually-retryable banner (ADR-0004 / S-15 — never
 * Background Sync, never a silent automatic retry).
 */
(function () {
    "use strict";

    if (typeof Dexie === "undefined") {
        // Dexie failed to load (e.g. offline first visit, CDN unreachable)
        // — offline drafts are simply unavailable this load; the online
        // form still works unmodified.
        return;
    }

    var form = document.querySelector("form[data-reporte-id][data-seccion-id]");
    if (!form) {
        return;
    }

    var db = window.reportesOfflineDB;
    if (!db) {
        // offline-db.js failed to load or run before this script — same
        // degrade-to-online-only contract as the Dexie-undefined guard above.
        return;
    }

    var RETARDO_MS = 400; // trailing-edge debounce (ADR-0001, no library);
    // above typical inter-keystroke gaps (~150-250ms), far below reaching
    // the submit button.

    var reporteId = Number(form.getAttribute("data-reporte-id"));
    var seccionId = form.getAttribute("data-seccion-id");
    var servidorActualizadoTexto = form.getAttribute("data-servidor-actualizado") || "";
    var servidorMs = servidorActualizadoTexto ? Date.parse(servidorActualizadoTexto) : 0;
    if (isNaN(servidorMs)) {
        servidorMs = 0;
    }
    // Change `vista-sincronizacion-pendientes`, Phase 2 (design's D4) —
    // captured once at parse time from the rendered `data-*` attrs so the
    // aggregated S-15 screen can display tipo/fecha with zero network
    // requests; persisted on every draft write below.
    var tipoNombre = form.getAttribute("data-tipo-nombre") || "";
    var fechaReporte = form.getAttribute("data-fecha-reporte") || "";

    var temporizadorDebounce = null;

    function serializarFormulario() {
        var datos = new FormData(form);
        var valores = {};
        datos.forEach(function (valor, nombre) {
            if (nombre === "csrfmiddlewaretoken") {
                return;
            }
            valores[nombre] = valor;
        });
        // Checkbox fields absent from FormData when unchecked (BooleanField,
        // required=False) — explicitly record them as false so a restore
        // can uncheck a previously-checked box.
        Array.prototype.forEach.call(
            form.querySelectorAll('input[type="checkbox"]'),
            function (casilla) {
                if (casilla.name && !(casilla.name in valores)) {
                    valores[casilla.name] = false;
                } else if (casilla.name && casilla.name in valores) {
                    valores[casilla.name] = casilla.checked;
                }
            }
        );
        return valores;
    }

    function escribirBorrador(estado) {
        var fila = {
            reporteId: reporteId,
            seccionId: seccionId,
            valores: serializarFormulario(),
            actualizadoEn: Date.now(),
            estado: estado,
            intentos: 0,
            ultimoError: null,
            tipoNombre: tipoNombre,
            fechaReporte: fechaReporte,
        };
        return db.borradores.put(fila);
    }

    function programarEscrituraDebounced() {
        if (temporizadorDebounce) {
            clearTimeout(temporizadorDebounce);
        }
        temporizadorDebounce = setTimeout(function () {
            escribirBorrador("borrador");
        }, RETARDO_MS);
    }

    function escribirInmediato() {
        if (temporizadorDebounce) {
            clearTimeout(temporizadorDebounce);
            temporizadorDebounce = null;
        }
        escribirBorrador("borrador");
    }

    // ---- Draft write wiring (design's Data Flow: input debounced, change
    // immediate) ----------------------------------------------------------

    form.addEventListener("input", function (evento) {
        if (evento.target && evento.target.closest("[data-borrador-prompt]")) {
            return;
        }
        programarEscrituraDebounced();
    });
    form.addEventListener("change", function (evento) {
        if (evento.target && evento.target.closest("[data-borrador-prompt]")) {
            return;
        }
        escribirInmediato();
    });

    // ---- Fetch-based submit (design's D4, "clear-on-success" Decision,
    // and the pendiente/fallo state machine) --------------------------------

    function obtenerIntentosPrevios() {
        return db.borradores.get([reporteId, seccionId]).then(function (fila) {
            return fila && typeof fila.intentos === "number" ? fila.intentos : 0;
        });
    }

    function marcarComo(estado, ultimoError) {
        return obtenerIntentosPrevios().then(function (previos) {
            var fila = {
                reporteId: reporteId,
                seccionId: seccionId,
                valores: serializarFormulario(),
                actualizadoEn: Date.now(),
                estado: estado,
                intentos: previos + 1,
                ultimoError: ultimoError,
                tipoNombre: tipoNombre,
                fechaReporte: fechaReporte,
            };
            return db.borradores.put(fila).catch(function () {
                // Dexie write failure still shows the banner from the
                // in-memory row — offline storage never blocks feedback.
            }).then(function () {
                mostrarBanner(fila);
            });
        });
    }

    function obtenerCsrfToken() {
        var campo = form.elements.csrfmiddlewaretoken;
        return campo ? campo.value : "";
    }

    function manejarResultadoEnvio(salida) {
        // Submission mechanics (fetch/CSRF/redirect classification/Dexie
        // reconciliation) now live in `window.reportesEnvioPaso.enviar`
        // (change `vista-sincronizacion-pendientes`, design's D2); this
        // caller keeps the exact same UI/navigation policy it always had.
        if (salida.resultado === "ok" || salida.resultado === "sesion_expirada") {
            limpiarBanner();
            location.assign(salida.url);
            return;
        }
        // "pendiente" | "fallo" — the helper already wrote the updated row
        // (intentos incremented); re-read it so the banner shows the
        // current count, matching pre-extraction behavior.
        db.borradores.get([reporteId, seccionId]).then(function (fila) {
            if (fila) {
                mostrarBanner(fila);
            }
        });
    }

    function intentarEnvio() {
        if (temporizadorDebounce) {
            clearTimeout(temporizadorDebounce);
            temporizadorDebounce = null;
        }
        if (!navigator.onLine) {
            marcarComo("pendiente", "sin_conexion");
            return;
        }
        window.reportesEnvioPaso
            .enviar({
                url: form.action,
                valores: serializarFormulario(),
                reporteId: reporteId,
                seccionId: seccionId,
                csrfToken: obtenerCsrfToken(),
            })
            .then(manejarResultadoEnvio);
    }

    form.addEventListener("submit", function (evento) {
        evento.preventDefault();
        intentarEnvio();
    });

    // ---- Restore-prompt UI ------------------------------------------------

    function crearPrompt() {
        var contenedor = document.createElement("div");
        contenedor.setAttribute("role", "alert");
        contenedor.setAttribute("data-borrador-prompt", "");
        contenedor.innerHTML =
            "<p>Hay cambios sin guardar de una sesión anterior. ¿Querés restaurarlos?</p>" +
            '<button type="button" data-borrador-restaurar>Restaurar</button>' +
            '<button type="button" data-borrador-descartar>Descartar</button>';
        form.insertAdjacentElement("beforebegin", contenedor);
        return contenedor;
    }

    function aplicarValoresAlFormulario(valores) {
        Object.keys(valores).forEach(function (nombre) {
            var campos = form.elements[nombre];
            if (!campos) {
                return;
            }
            var lista = campos.length !== undefined && campos.nodeType === undefined
                ? Array.prototype.slice.call(campos)
                : [campos];
            lista.forEach(function (campo) {
                if (campo.type === "checkbox") {
                    campo.checked = Boolean(valores[nombre]);
                } else if (campo.type === "radio") {
                    campo.checked = campo.value === valores[nombre];
                } else {
                    campo.value = valores[nombre];
                }
                campo.dispatchEvent(new Event("input", { bubbles: true }));
                campo.dispatchEvent(new Event("change", { bubbles: true }));
            });
        });
    }

    function mostrarPrompt(fila) {
        var prompt = crearPrompt();
        prompt.querySelector("[data-borrador-restaurar]").addEventListener(
            "click",
            function () {
                aplicarValoresAlFormulario(fila.valores);
                prompt.remove();
            }
        );
        prompt.querySelector("[data-borrador-descartar]").addEventListener(
            "click",
            function () {
                db.borradores.delete([reporteId, seccionId]);
                prompt.remove();
            }
        );
    }

    // ---- Retry banner UI (design's D6 — mirrors the restore-prompt pattern
    // above; `pendiente`/`fallo` states, upload-queue spec's "Manual Retry
    // Affordance") -----------------------------------------------------------

    function limpiarBanner() {
        var banner = document.querySelector("[data-borrador-banner]");
        if (banner) {
            banner.remove();
        }
    }

    function mensajeBanner(fila) {
        if (fila.estado === "pendiente") {
            return "Sin conexión — pendiente de subir (" + fila.intentos + ")";
        }
        return "No se pudo subir (" + fila.intentos + " intentos)";
    }

    function mostrarBanner(fila) {
        limpiarBanner();
        var contenedor = document.createElement("div");
        contenedor.setAttribute("role", "alert");
        contenedor.setAttribute("data-borrador-banner", "");
        contenedor.innerHTML =
            "<p>" + mensajeBanner(fila) + "</p>" +
            '<button type="button" data-borrador-reintentar>Reintentar</button>';
        form.insertAdjacentElement("beforebegin", contenedor);
        contenedor.querySelector("[data-borrador-reintentar]").addEventListener(
            "click",
            function () {
                // Re-serializes the *current* form (the user may have
                // edited it while pendiente/fallo) and re-runs the fetch
                // submit — transitions back to "enviando" (design's state
                // table).
                intentarEnvio();
            }
        );
        return contenedor;
    }

    // ---- Reconciliation on load (design's state table) --------------------

    function reconciliar() {
        db.borradores.get([reporteId, seccionId]).then(function (fila) {
            if (!fila) {
                return;
            }

            if (fila.estado === "pendiente" || fila.estado === "fallo") {
                // Restore the banner with the existing intentos/ultimoError
                // values — no automatic retry (ADR-0004/S-15).
                mostrarBanner(fila);
                return;
            }

            if (fila.estado === "enviando") {
                if (fila.seccionId !== seccionId) {
                    // Redirect proved the POST landed elsewhere — stale.
                    db.borradores.delete([reporteId, seccionId]);
                    return;
                }
                if (fila.actualizadoEn <= servidorMs) {
                    // Last section redirects to itself — server already has it.
                    db.borradores.delete([reporteId, seccionId]);
                    return;
                }
                // Ambiguity resolves toward keeping the draft (clock skew
                // must never delete data) — demote back to "borrador" and
                // prompt.
                db.borradores.update([reporteId, seccionId], { estado: "borrador" });
                mostrarPrompt(fila);
                return;
            }

            // estado === "borrador"
            if (fila.actualizadoEn <= servidorMs) {
                db.borradores.delete([reporteId, seccionId]);
                return;
            }
            mostrarPrompt(fila);
        });
    }

    reconciliar();
})();
