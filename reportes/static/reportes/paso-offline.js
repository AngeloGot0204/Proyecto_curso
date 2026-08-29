/**
 * Client-side offline draft layer for the `paso` wizard step (change
 * `capa-offline`; design's "Technical Approach", "Data Flow", "Interfaces /
 * Contracts"). Vanilla JS only, hand-rolled debounce, no build step
 * (ADR-0001) — Dexie is the sole third-party dependency, loaded via CDN in
 * `paso.html`. No JS test runner exists in this project (spec's Out of
 * Scope); coverage is the manual DevTools script in tasks.md Phase 5.
 *
 * Depends on the rendered-attribute contract on the step `<form>`:
 * `data-reporte-id`, `data-seccion-id`, `data-servidor-actualizado`
 * (design's File Changes / Interfaces sections).
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

    var db = new Dexie("reportes-offline");
    db.version(1).stores({
        borradores: "[reporteId+seccionId], reporteId, estado",
    });

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

    // ---- Submit handler (design's "clear-on-success" Decision) ----------

    form.addEventListener("submit", function (evento) {
        evento.preventDefault();
        if (temporizadorDebounce) {
            clearTimeout(temporizadorDebounce);
            temporizadorDebounce = null;
        }
        escribirBorrador("enviando")
            .catch(function () {
                // Any Dexie rejection still lets the submit proceed —
                // offline storage never blocks the user (design's explicit
                // contract).
            })
            .then(function () {
                form.submit();
            });
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

    // ---- Reconciliation on load (design's state table) --------------------

    function reconciliar() {
        db.borradores.get([reporteId, seccionId]).then(function (fila) {
            if (!fila) {
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
