/**
 * Aggregated cross-report pending/failed sync list (S-15; change
 * `vista-sincronizacion-pendientes`, Phase 4, design's D1/D2/D3; spec
 * `sincronizacion-pendientes`, Requirements "Aggregated Cross-Report
 * Pending List", "Retry-Only Actions No Discard", "Retry Reuses
 * Upload-Queue Submission Contract"). Renders entirely from the local
 * Dexie `borradores` store — zero server queries (design D1) — so the
 * screen works fully offline.
 *
 * Depends on `sincronizacion.html`'s shell hooks: `[data-sincronizacion-form]`
 * (CSRF token source), `[data-url-paso-plantilla]` (D3 retry-URL template,
 * literal `"0"` reporte-id segment + `"__SECCION__"` placeholder),
 * `[data-sincronizacion-lista]`, `[data-sincronizacion-vacio]`.
 *
 * Reuses `window.reportesEnvioPaso.enviar` (D2) for the actual retry POST —
 * the helper owns fetch/CSRF/redirect classification/Dexie reconciliation;
 * this module only owns rendering and navigation-on-session-expiry, mirroring
 * `paso-offline.js`'s `manejarResultadoEnvio` caller contract.
 *
 * Vanilla JS only, no build step (ADR-0001). No JS test runner exists in
 * this project (spec's Out of Scope); coverage is the manual DevTools
 * script in tasks.md Phase 4 (task 4.3).
 */
(function () {
    "use strict";

    if (typeof Dexie === "undefined") {
        // Same degrade-to-online-only contract as every other offline
        // script: no Dexie means no local list to render.
        return;
    }

    var lista = document.querySelector("[data-sincronizacion-lista]");
    var vacio = document.querySelector("[data-sincronizacion-vacio]");
    var plantillaUrl = document.querySelector("[data-url-paso-plantilla]");
    var formulario = document.querySelector("[data-sincronizacion-form]");
    if (!lista || !vacio || !plantillaUrl || !formulario) {
        // Shell hooks missing — nothing to bind against.
        return;
    }

    var db = window.reportesOfflineDB;
    if (!db) {
        // offline-db.js failed to load or run before this script — same
        // degrade-to-online-only contract as paso-offline.js/adjuntos.js.
        return;
    }

    function csrfToken() {
        var campo = formulario.elements.csrfmiddlewaretoken;
        return campo ? campo.value : "";
    }

    function construirUrlReintento(reporteId, seccionId) {
        // D3 — the placeholder is a real Django-reversed path with a
        // literal `0` reporte-id segment (e.g. "/reportes/0/paso/
        // __SECCION__/"); replace only the `/0/` segment so a `seccionId`
        // that happens to contain "0" is never mistaken for it.
        var plantilla = plantillaUrl.getAttribute("data-url-paso-plantilla") || "";
        return plantilla
            .replace("/0/", "/" + reporteId + "/")
            .replace("__SECCION__", encodeURIComponent(seccionId));
    }

    function etiquetaEstado(estado) {
        return estado === "pendiente" ? "Pendiente" : "No se pudo subir";
    }

    function crearFila(fila) {
        var item = document.createElement("li");
        item.className = "lista__tarjeta";
        item.setAttribute("data-sincronizacion-fila", "");

        var tipo = document.createElement("span");
        tipo.className = "lista__enlace";
        tipo.textContent = fila.tipoNombre || "Reporte";
        item.appendChild(tipo);

        var meta = document.createElement("span");
        meta.className = "lista__meta mono";
        meta.textContent = (fila.fechaReporte || "") + " · " + fila.seccionId;
        item.appendChild(meta);

        var chip = document.createElement("span");
        chip.className =
            fila.estado === "pendiente" ? "chip chip--borde" : "chip chip--ambar";
        chip.textContent = etiquetaEstado(fila.estado);
        item.appendChild(chip);

        var boton = document.createElement("button");
        boton.type = "button";
        boton.className = "acciones__secundario";
        boton.setAttribute("data-sincronizacion-reintentar", "");
        boton.textContent = "Reintentar";
        boton.addEventListener("click", function () {
            reintentar(fila, boton);
        });
        item.appendChild(boton);

        return item;
    }

    function renderizar() {
        return db.borradores
            .where("estado")
            .anyOf("pendiente", "fallo")
            .toArray()
            .then(function (filas) {
                filas.sort(function (a, b) {
                    return (b.actualizadoEn || 0) - (a.actualizadoEn || 0);
                });

                lista.innerHTML = "";
                if (filas.length === 0) {
                    lista.hidden = true;
                    vacio.hidden = false;
                    return;
                }
                vacio.hidden = true;
                lista.hidden = false;
                filas.forEach(function (fila) {
                    lista.appendChild(crearFila(fila));
                });
            });
    }

    function reintentar(fila, boton) {
        // Single-action-only: disable this row's button for the duration
        // of its own request, never touching any other row (spec/tasks 4.3
        // "single-action-only rows").
        boton.disabled = true;
        boton.textContent = "Reintentando…";

        window.reportesEnvioPaso
            .enviar({
                url: construirUrlReintento(fila.reporteId, fila.seccionId),
                valores: fila.valores,
                reporteId: fila.reporteId,
                seccionId: fila.seccionId,
                csrfToken: csrfToken(),
            })
            .then(function (salida) {
                if (salida.resultado === "sesion_expirada") {
                    // Row stays in Dexie (helper never deletes on this
                    // outcome) — navigate to re-authenticate, same policy
                    // as `paso-offline.js`'s `manejarResultadoEnvio`.
                    location.assign(salida.url);
                    return;
                }
                // "ok" (helper deleted the row) or "pendiente"/"fallo"
                // (helper updated it) — re-render from the current Dexie
                // state either way.
                renderizar();
            });
    }

    renderizar();
})();
