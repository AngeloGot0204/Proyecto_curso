/**
 * Auto-dismiss + manual close for the flash-message toasts rendered by
 * `base.html` (`[data-toasts] > .aviso`). Vanilla JS IIFE, no build step
 * (ADR-0001), mirroring `conexion-chip.js`'s isolation/no-op-when-absent
 * pattern — this file touches only `[data-toasts]` and its own children,
 * nothing else on the page.
 *
 * Errors stay on screen until the user dismisses them (a mistake worth
 * reading twice); success/info/warning/debug auto-dismiss after a few
 * seconds so they don't pile up across a session.
 */
(function () {
    "use strict";

    var contenedor = document.querySelector("[data-toasts]");
    if (!contenedor) {
        return;
    }

    var DURACION_MS = 5000;

    function cerrar(aviso) {
        aviso.remove();
    }

    Array.prototype.forEach.call(contenedor.querySelectorAll(".aviso"), function (aviso) {
        var boton = aviso.querySelector("[data-cerrar-aviso]");
        if (boton) {
            boton.addEventListener("click", function () {
                cerrar(aviso);
            });
        }

        if (!aviso.classList.contains("aviso--error")) {
            setTimeout(function () {
                cerrar(aviso);
            }, DURACION_MS);
        }
    });
})();
