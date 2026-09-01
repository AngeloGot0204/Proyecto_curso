/**
 * Live connection-state chip for `.barra-pantalla` (change
 * `chip-conexion-en-vivo`; design's "Technical Approach", "Data Flow",
 * "Interfaces / Contracts"). Vanilla JS IIFE, no build step (ADR-0001),
 * loaded with `defer` from `templates/base.html` so it runs after DOM parse
 * and before `DOMContentLoaded` — the synchronous initial `navigator.onLine`
 * read the spec requires, with no event wait.
 *
 * Strict isolation from `paso-offline.js` (design's Decision "Strict
 * isolation from paso-offline.js"): separate file, separate IIFE, no
 * `window.*` export, DOM contract limited to `[data-chip-conexion]`. The
 * only shared surface with `paso-offline.js` is a read-only
 * `navigator.onLine` read; this file never touches the draft-restore
 * banner/prompt nodes or submit gating.
 */
(function () {
    "use strict";

    var chip = document.querySelector("[data-chip-conexion]");
    if (!chip) {
        // No `.barra-pantalla` on this screen (e.g. `/login/`) — nothing to
        // do, script-optional degrade (design's Technical Approach).
        return;
    }

    function pintar(enLinea) {
        if (enLinea) {
            chip.className = "chip barra-pantalla__conexion chip--borde-gris";
            chip.textContent = "en línea";
            chip.setAttribute("data-estado", "en-linea");
        } else {
            chip.className = "chip barra-pantalla__conexion chip--borde";
            chip.textContent = "offline";
            chip.setAttribute("data-estado", "offline");
        }
        chip.hidden = false;
    }

    // Synchronous initial read (spec: "Initial load reflects current
    // connection state without waiting for an event").
    pintar(navigator.onLine);

    window.addEventListener("online", function () {
        pintar(navigator.onLine);
    });
    window.addEventListener("offline", function () {
        pintar(navigator.onLine);
    });
})();
