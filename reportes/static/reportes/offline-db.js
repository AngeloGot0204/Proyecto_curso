/**
 * Shared Dexie schema module (change `sincronizacion-numero-registro`,
 * design's D5 — "Shared Dexie schema module"). Owns the single `.version()`
 * declaration for the `reportes-offline` IndexedDB database and exposes it
 * as `window.reportesOfflineDB` for every consumer script to reuse.
 *
 * Two scripts each calling `.version()` on the same database name with
 * different store sets produces an inconsistent upgrade — so only this file
 * ever does that. `paso-offline.js` and `nuevo-reporte.js` (#12,
 * forward-looking, out of scope for this PR) both read `window.reportesOfflineDB`
 * instead of opening their own `Dexie(...)` instance.
 *
 * `borradores` keeps its original v1 shape (`[reporteId+seccionId]` primary
 * key, `reporteId`/`estado` indexes) — the `pendiente`/`fallo` `estado`
 * values and the `intentos`/`ultimoError` fields added by the upload-queue
 * rework are data, not schema, so no index change is required for them.
 * `nuevos` is new, reserved for #12's forward-looking `id_local` generation.
 *
 * Vanilla JS only, no build step (ADR-0001). Must be loaded via a plain
 * `<script>` tag BEFORE any consumer script (e.g. `paso-offline.js`) in the
 * page template, and after the Dexie CDN `<script>` tag.
 */
(function () {
    "use strict";

    if (typeof Dexie === "undefined") {
        // Dexie failed to load (e.g. offline first visit, CDN unreachable)
        // — consumers already guard for `window.reportesOfflineDB` being
        // absent and degrade to online-only behavior.
        return;
    }

    var db = new Dexie("reportes-offline");
    db.version(2).stores({
        borradores: "[reporteId+seccionId], reporteId, estado",
        nuevos: "codigoTipo",
    });

    window.reportesOfflineDB = db;
})();
