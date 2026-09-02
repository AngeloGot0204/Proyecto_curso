/*
 * Confirmation prompt for destructive form submissions.
 *
 * Replaces the inline `onsubmit="return confirm('…')"` attributes on the
 * delete forms in `mis_reportes.html`, `paso.html` and `adjuntos.html`. An
 * inline event-handler attribute is inline script as far as CSP is
 * concerned, so those attributes alone would have forced
 * `script-src 'unsafe-inline'` and gutted the policy
 * (SECURITY-REPORT.md F-02).
 *
 * Contract: put `data-confirmar="<message>"` on the <form>. Submitting it
 * asks first; cancelling stops the submit. A form without the attribute is
 * untouched, so nothing else on the page changes behavior.
 *
 * Listener is attached on the document, not per form, so forms rendered
 * after this script runs are covered too.
 */
(function () {
    "use strict";

    document.addEventListener(
        "submit",
        function (evento) {
            var formulario = evento.target;
            if (!formulario || !formulario.hasAttribute) {
                return;
            }
            var mensaje = formulario.getAttribute("data-confirmar");
            if (!mensaje) {
                return;
            }
            if (!window.confirm(mensaje)) {
                evento.preventDefault();
            }
        },
        true
    );
})();
