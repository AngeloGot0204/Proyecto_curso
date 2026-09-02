/*
 * S-03 "Nuevo reporte" form handling (spec `reporte-idempotent-creation`).
 *
 * Extracted verbatim from `seleccion_tipo.html`'s inline <script> so the
 * page carries no inline JavaScript and the Content-Security-Policy can
 * declare `script-src 'self'` without `'unsafe-inline'`
 * (SECURITY-REPORT.md F-02). Behavior is unchanged.
 */
(function () {
    "use strict";

    document.querySelectorAll(".js-nuevo-reporte").forEach(function (form) {
        form.addEventListener("submit", function () {
            // id_local: the same value on a double-click resubmit makes the
            // server-side get_or_create() idempotent instead of creating a
            // duplicate Reporte.
            var campo = form.querySelector(".js-id-local");
            if (!campo.value) {
                campo.value = crypto.randomUUID();
            }
            var boton = form.querySelector("button[type=submit]");
            boton.disabled = true;
        });
    });
})();
