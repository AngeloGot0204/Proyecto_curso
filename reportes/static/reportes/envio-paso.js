/**
 * Form-independent step submission helper (change
 * `vista-sincronizacion-pendientes`, design's D2/D8; Data Flow / Interfaces
 * sections). Shared by `paso-offline.js` (this change's Phase 1) and, from
 * Phase 4 on, `sincronizacion.js`'s per-row "Reintentar" action — so it MUST
 * work against a stored Dexie row's `valores` without a live step `<form>`
 * in the DOM.
 *
 * Owns fetch + CSRF + redirect classification + Dexie `borradores`
 * reconciliation (D2); the caller keeps UI/navigation policy — it never
 * navigates or renders on the helper's behalf, it only inspects the
 * returned outcome.
 *
 * Vanilla JS, no build step (ADR-0001). IIFE exposing
 * `window.reportesEnvioPaso`.
 */
(function () {
    "use strict";

    function coercionSeguraDeId(valor) {
        // D8 — a corrupt local row must never compose an arbitrary POST
        // path / Dexie key.
        return typeof valor === "number" ? valor : Number(valor);
    }

    function construirFormData(valores, csrfToken) {
        var datos = new FormData();
        Object.keys(valores || {}).forEach(function (nombre) {
            var valor = valores[nombre];
            if (valor === false) {
                // Unchecked checkbox — omitted entirely (D8): Django's
                // CheckboxInput.value_from_datadict treats ANY present
                // non-"false" value as True.
                return;
            }
            if (valor === true) {
                datos.append(nombre, "on");
                return;
            }
            datos.append(nombre, valor);
        });
        if (csrfToken) {
            datos.append("csrfmiddlewaretoken", csrfToken);
        }
        return datos;
    }

    function obtenerDB() {
        return window.reportesOfflineDB || null;
    }

    /**
     * Writes `campos` onto the `borradores` row for this step, PRESERVING any
     * field this helper does not manage.
     *
     * Dexie's `put()` replaces the whole record, so writing an object literal
     * silently drops every key absent from it. `paso-offline.js` stores
     * `tipoNombre`/`fechaReporte` when it first saves the draft (spec
     * `sincronizacion-pendientes` — "Draft Write Captures Display Metadata"),
     * and this helper knows nothing about them: replacing the record wiped
     * them on every retry, leaving S-15 rendering "Reporte · <seccion>" with
     * no type or date — exactly when a failed upload makes that information
     * most necessary.
     *
     * Merging over the previous row keeps the contract open: a field added
     * later by any other writer survives here without this helper being taught
     * about it.
     */
    function fusionarEnBorrador(db, reporteId, seccionId, campos) {
        return db.borradores
            .get([reporteId, seccionId])
            .catch(function () {
                // Unreadable previous row: fall back to writing just `campos`.
                return undefined;
            })
            .then(function (previa) {
                var fila = Object.assign({}, previa || {}, campos);
                fila.reporteId = reporteId;
                fila.seccionId = seccionId;
                return db.borradores.put(fila);
            })
            .catch(function () {
                // Dexie write failure never blocks the caller's outcome.
            });
    }

    function reconciliarEnEnvio(db, reporteId, seccionId, valores) {
        if (!db) {
            return Promise.resolve();
        }
        return fusionarEnBorrador(db, reporteId, seccionId, {
            valores: valores,
            actualizadoEn: Date.now(),
            estado: "enviando",
            intentos: 0,
            ultimoError: null,
        });
    }

    function intentosPrevios(db, reporteId, seccionId) {
        if (!db) {
            return Promise.resolve(0);
        }
        return db.borradores.get([reporteId, seccionId]).then(function (fila) {
            return fila && typeof fila.intentos === "number" ? fila.intentos : 0;
        });
    }

    function reconciliarResultado(db, reporteId, seccionId, valores, resultado, error) {
        if (!db) {
            return Promise.resolve();
        }
        if (resultado === "ok") {
            return db.borradores.delete([reporteId, seccionId]).catch(function () {
                // Deletion failure never blocks reporting the outcome.
            });
        }
        // "sesion_expirada" reconciles to Dexie `estado: "fallo"` (matching
        // the pre-extraction `marcarComo("fallo", "sesion_expirada")`
        // contract) — the specific case is still identifiable via
        // `ultimoError`, and `reconciliar()`'s on-load state machine only
        // recognizes `pendiente`/`fallo`/`enviando`/`borrador` estados.
        var estado = resultado === "sesion_expirada" ? "fallo" : resultado;
        return intentosPrevios(db, reporteId, seccionId).then(function (previos) {
            return fusionarEnBorrador(db, reporteId, seccionId, {
                valores: valores,
                actualizadoEn: Date.now(),
                estado: estado,
                intentos: previos + 1,
                ultimoError: error,
            });
        });
    }

    function clasificarRespuesta(respuesta) {
        var urlFinal = new URL(respuesta.url, window.location.href);
        if (urlFinal.pathname === "/login/") {
            // Session expired mid-submit — the caller decides whether/how
            // to navigate (D2); the row is kept, never deleted here.
            return { resultado: "sesion_expirada", url: respuesta.url, error: "sesion_expirada" };
        }
        if (respuesta.ok || respuesta.redirected) {
            return { resultado: "ok", url: respuesta.url, error: null };
        }
        if (respuesta.status >= 400) {
            return { resultado: "fallo", url: respuesta.url, error: "http_" + respuesta.status };
        }
        return { resultado: "fallo", url: respuesta.url, error: "respuesta_inesperada" };
    }

    function enviar(opciones) {
        opciones = opciones || {};
        var url = opciones.url;
        var valores = opciones.valores || {};
        var reporteId = coercionSeguraDeId(opciones.reporteId);
        var seccionId = opciones.seccionId;
        var csrfToken = opciones.csrfToken;
        var db = obtenerDB();

        return reconciliarEnEnvio(db, reporteId, seccionId, valores)
            .then(function () {
                return fetch(url, {
                    method: "POST",
                    body: construirFormData(valores, csrfToken),
                    credentials: "same-origin",
                    redirect: "follow",
                });
            })
            .then(function (respuesta) {
                var salida = clasificarRespuesta(respuesta);
                return reconciliarResultado(
                    db, reporteId, seccionId, valores, salida.resultado, salida.error
                ).then(function () {
                    return salida;
                });
            })
            .catch(function () {
                // Network error (offline mid-request, DNS failure, server
                // unreachable, etc.) — never a silent retry (ADR-0004/S-15);
                // mark `pendiente` and let the caller decide UI/navigation.
                return reconciliarResultado(
                    db, reporteId, seccionId, valores, "pendiente", "error_de_red"
                ).then(function () {
                    return { resultado: "pendiente", url: url, error: "error_de_red" };
                });
            });
    }

    window.reportesEnvioPaso = { enviar: enviar };
})();
