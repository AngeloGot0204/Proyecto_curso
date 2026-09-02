/*
 * Service worker registration, shared by `paso.html` and
 * `sincronizacion.html` (change `capa-offline`).
 *
 * Extracted from two identical inline <script> blocks so the pages carry no
 * inline JavaScript, which is what lets the Content-Security-Policy declare
 * `script-src 'self'` without `'unsafe-inline'` (SECURITY-REPORT.md F-02).
 * A CSP that has to allow inline scripts blocks almost nothing worth
 * blocking, so this extraction is the whole point, not tidying.
 *
 * Registration failure must never block the page: offline support degrades
 * silently to online-only behavior, and draft persistence still works via
 * Dexie regardless of the registration outcome.
 */
(function () {
    "use strict";

    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", function () {
        navigator.serviceWorker.register("/sw.js").catch(function () {
            // Deliberately silent — see header.
        });
    });
})();
