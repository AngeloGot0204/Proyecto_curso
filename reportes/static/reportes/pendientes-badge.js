/**
 * Entry-point badge for S-02 ("Mis reportes") pointing at the S-15
 * aggregated sync screen (change `vista-sincronizacion-pendientes`,
 * Phase 5, design's D5; spec `sincronizacion-pendientes`, Requirement
 * "Entry Point From Mis Reportes"). Deliberately its own file, NOT folded
 * into `sincronizacion.js` (D5's "one-file-per-screen defensive-opening
 * convention") — `mis_reportes.html` must never ship the full list
 * renderer, only a cheap `count()` against the shared Dexie `borradores`
 * store.
 *
 * Depends on `mis_reportes.html`'s `[data-badge-pendientes]` hook, rendered
 * `hidden` by default (design D5 "Chip renders hidden, JS reveals it"
 * precedent from `chip-conexion-en-vivo`).
 *
 * Vanilla JS only, no build step (ADR-0001). No JS test runner exists in
 * this project (spec's Out of Scope); coverage is the manual DevTools
 * script in tasks.md Phase 5 (task 5.4).
 */
(function () {
    "use strict";

    if (typeof Dexie === "undefined") {
        // Same degrade-to-online-only contract as every other offline
        // script — badge simply stays hidden this load.
        return;
    }

    var insignia = document.querySelector("[data-badge-pendientes]");
    if (!insignia) {
        return;
    }

    var db = window.reportesOfflineDB;
    if (!db) {
        // offline-db.js failed to load or run before this script.
        return;
    }

    db.borradores
        .where("estado")
        .anyOf("pendiente", "fallo")
        .count()
        .then(function (cantidad) {
            // Explicit both branches (not just "if > 0"): a stale cached
            // copy of this file, or the markup starting without `hidden`
            // for any reason, must never leave a visible "0" badge — the
            // hidden state is asserted every run, not only inherited from
            // the template default.
            if (cantidad > 0) {
                insignia.textContent = String(cantidad);
                insignia.hidden = false;
            } else {
                insignia.hidden = true;
            }
        });
})();
