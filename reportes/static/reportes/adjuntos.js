/**
 * Client-side attachment pipeline for S-08 ("croquis/evidencia") upload
 * (backlog #11, spec `adjuntos-reporte`; design's D3 "Client pipeline in
 * its own file, both CDN libraries optional", D4 "offline-db.js
 * version(3)"). Deliberately its own file, NOT folded into
 * `paso-offline.js` (design D2/D3): an attachment's own dedicated `fetch`
 * call to `/reportes/<id>/adjuntos/subir/` must never touch the step's
 * `FormData` POST to `form.action`, so a rejected/offline attachment can
 * never block or roll back the step's field values (spec "Per-Attachment
 * Failure Isolation", "Offline Queueing Through Shared Dexie Schema").
 *
 * Vanilla JS only, no build step (ADR-0001). Two third-party libraries
 * are used, both vendored under `static/vendor/` (SECURITY-REPORT.md F-02;
 * they used to load from a CDN with no `integrity`) and both strictly
 * best-effort, feature-detected via
 * `typeof … === "function"` (never a hard import, mirroring the
 * `typeof Dexie === "undefined"` guard both existing offline scripts open
 * with):
 *   - `window.heic2any` — HEIC/HEIF → JPEG conversion, run BEFORE
 *     compression (spec "Client-Side HEIC Conversion Before Compression").
 *   - `window.imageCompression` (`browser-image-compression`'s UMD global)
 *     — best-effort size reduction (spec "Client-Side Best-Effort
 *     Compression with Fallback").
 * Either library missing or throwing falls back to the ORIGINAL file,
 * still checked against the 8MiB ceiling before any upload attempt —
 * capture is never hard-blocked by a library that did not load (design D3
 * pipeline diagram). Self-hosting makes that far less likely than it was,
 * but the guards stay: they also cover a decode error on a real file.
 *
 * Depends on the rendered-attribute contract on a dedicated container
 * (deliberately decoupled from `paso-offline.js`'s `form[data-reporte-id]
 * [data-seccion-id]` contract, for isolation — design D2):
 * `[data-adjuntos][data-reporte-id][data-seccion-id][data-adjuntos-url]`,
 * containing `input[type="file"][data-adjunto]`. No-op when absent,
 * mirroring `nuevo-reporte.js`'s D7 defensive-opening pattern. The Dexie
 * schema itself lives in `offline-db.js` (D4), loaded before this file and
 * exposed as `window.reportesOfflineDB`; the CSRF token is read from the
 * step form's existing `{% csrf_token %}` hidden input, so this module
 * never touches cookies directly.
 *
 * No JS test runner exists in this project (spec's Out of Scope); coverage
 * is the manual DevTools script in tasks.md Phase 6.
 */
(function () {
    "use strict";

    if (typeof Dexie === "undefined") {
        // Dexie failed to load — offline queueing is unavailable this
        // load; same degrade contract as paso-offline.js/nuevo-reporte.js.
        // Since vendoring (F-02) this no longer happens on a first visit
        // without signal, which is exactly when the offline layer matters.
        return;
    }

    var contenedor = document.querySelector(
        "[data-adjuntos][data-reporte-id][data-seccion-id][data-adjuntos-url]"
    );
    if (!contenedor) {
        // No host template includes this hook on this page (any section
        // other than S-08) — no-op.
        return;
    }

    var entrada = contenedor.querySelector('input[type="file"][data-adjunto]');
    if (!entrada) {
        return;
    }

    var db = window.reportesOfflineDB;
    if (!db) {
        // offline-db.js failed to load or run before this script — same
        // degrade-to-online-only contract as the Dexie-undefined guard.
        return;
    }

    var TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024; // 8MiB (design D3, D7)

    // Server mirror (design's Interfaces/Contracts) — content-type keys;
    // extensions kept only as a fallback detector, since some browsers
    // report an empty `File.type` for HEIC/HEIF.
    var FORMATOS_PERMITIDOS = {
        "image/jpeg": true,
        "image/png": true,
        "image/webp": true,
        "image/heic": true,
        "image/heif": true,
    };
    var EXTENSIONES_PERMITIDAS = [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"];
    var EXTENSIONES_HEIC = [".heic", ".heif"];

    var reporteId = Number(contenedor.getAttribute("data-reporte-id"));
    var seccionId = contenedor.getAttribute("data-seccion-id");
    var urlSubida = contenedor.getAttribute("data-adjuntos-url");
    var lista = contenedor.querySelector("[data-adjuntos-lista]");
    var selectorCategoria = contenedor.querySelector("[data-adjunto-categoria]");

    function csrfToken() {
        var campo = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return campo ? campo.value : "";
    }

    function categoriaSeleccionada() {
        return selectorCategoria && selectorCategoria.value ? selectorCategoria.value : "evidencia";
    }

    function extension(nombre) {
        var indice = nombre.lastIndexOf(".");
        return indice === -1 ? "" : nombre.slice(indice).toLowerCase();
    }

    function esFormatoPermitido(archivo) {
        if (archivo.type && FORMATOS_PERMITIDOS[archivo.type]) {
            return true;
        }
        return EXTENSIONES_PERMITIDAS.indexOf(extension(archivo.name || "")) !== -1;
    }

    function esHeic(archivo) {
        if (archivo.type === "image/heic" || archivo.type === "image/heif") {
            return true;
        }
        return EXTENSIONES_HEIC.indexOf(extension(archivo.name || "")) !== -1;
    }

    // ---- Chip UI (per-attachment, mirrors paso-offline.js's retry-banner
    // pattern but scoped to one list entry per attachment instead of one
    // shared banner — spec "Per-Attachment Failure Isolation") --------------

    function crearChip(texto) {
        if (!lista) {
            return null;
        }
        var item = document.createElement("li");
        item.setAttribute("data-adjunto-chip", "");
        item.textContent = texto;
        lista.appendChild(item);
        return item;
    }

    function actualizarChip(chip, texto, conReintento, alReintentar) {
        if (!chip) {
            return;
        }
        chip.textContent = texto;
        if (conReintento) {
            var boton = document.createElement("button");
            boton.type = "button";
            boton.setAttribute("data-adjunto-reintentar", "");
            boton.textContent = "Reintentar";
            boton.addEventListener("click", alReintentar);
            chip.appendChild(boton);
        }
    }

    // ---- CDN pipeline (design D3 diagram) -----------------------------------

    function convertirSiEsHeic(archivo) {
        if (!esHeic(archivo)) {
            return Promise.resolve(archivo);
        }
        if (typeof window.heic2any !== "function") {
            // Library unreachable — fall back to the original (spec "CDN
            // unreachable falls back to original file").
            return Promise.resolve(archivo);
        }
        return window
            .heic2any({ blob: archivo, toType: "image/jpeg" })
            .then(function (resultado) {
                var salida = Array.isArray(resultado) ? resultado[0] : resultado;
                var nombre = (archivo.name || "adjunto").replace(/\.[^.]+$/, "") + ".jpg";
                return new File([salida], nombre, { type: "image/jpeg" });
            })
            .catch(function () {
                // Conversion failure — fall back to the original (spec
                // "Conversion or compression failure falls back to
                // original file").
                return archivo;
            });
    }

    function comprimirSiPosible(archivo) {
        if (typeof window.imageCompression !== "function") {
            return Promise.resolve(archivo);
        }
        return window
            .imageCompression(archivo, { maxSizeMB: 2, maxWidthOrHeight: 2000 })
            .catch(function () {
                return archivo;
            });
    }

    function procesarArchivo(archivoOriginal) {
        return convertirSiEsHeic(archivoOriginal).then(comprimirSiPosible);
    }

    // ---- Upload / offline queue (design D2, D4, Data Flow) ------------------

    function subirAlServidor(archivo, categoria) {
        var datos = new FormData();
        datos.append("archivo", archivo, archivo.name || "adjunto");
        datos.append("seccion_id", seccionId);
        datos.append("categoria", categoria);
        datos.append("csrfmiddlewaretoken", csrfToken());
        // Its OWN fetch call, deliberately separate from paso-offline.js's
        // `fetch(form.action, {body: new FormData(form)})` — spec "Offline
        // Queueing Through Shared Dexie Schema".
        return fetch(urlSubida, {
            method: "POST",
            body: datos,
            credentials: "same-origin",
            redirect: "follow",
        });
    }

    function encolar(archivo, categoria, ultimoError) {
        var fila = {
            reporteId: reporteId,
            seccionId: seccionId,
            categoria: categoria,
            blob: archivo,
            nombreOriginal: archivo.name || "adjunto",
            formatoOriginal: archivo.type || "",
            tamanoBytes: archivo.size,
            estado: "pendiente",
            intentos: 0,
            ultimoError: ultimoError || null,
            creadoEn: Date.now(),
        };
        return db.adjuntos_pendientes.add(fila).then(function (id) {
            fila.id = id;
            return fila;
        });
    }

    function borrarSiEncolado(fila) {
        if (fila && fila.id) {
            return db.adjuntos_pendientes.delete(fila.id);
        }
        return Promise.resolve();
    }

    function manejarRespuesta(respuesta, chip, archivo, categoria, filaExistente) {
        var urlFinal = new URL(respuesta.url, window.location.href);
        if (urlFinal.pathname === "/login/") {
            // Session expired mid-upload — keep/create the queued row
            // intact, exactly as paso-offline.js does for the step form
            // (design's Data Flow: "302 /login/ → estado:'fallo' (fila
            // intacta)").
            var promesaFila = filaExistente
                ? db.adjuntos_pendientes
                      .update(filaExistente.id, { estado: "fallo", ultimoError: "sesion_expirada" })
                      .then(function () {
                          return filaExistente;
                      })
                : encolar(archivo, categoria, "sesion_expirada").then(function (fila) {
                      return db.adjuntos_pendientes
                          .update(fila.id, { estado: "fallo" })
                          .then(function () {
                              fila.estado = "fallo";
                              return fila;
                          });
                  });
            return promesaFila.then(function (fila) {
                actualizarChip(chip, "No se pudo subir — sesión expirada.", true, function () {
                    reintentarFila(fila, chip);
                });
            });
        }
        if (respuesta.status === 201) {
            actualizarChip(chip, "Adjunto subido.", false);
            return borrarSiEncolado(filaExistente);
        }
        if (respuesta.status === 400) {
            return respuesta
                .json()
                .catch(function () {
                    return {};
                })
                .then(function (cuerpo) {
                    actualizarChip(chip, "Adjunto rechazado (" + (cuerpo.error || "error") + ").", false);
                    return borrarSiEncolado(filaExistente);
                });
        }
        if (respuesta.status === 404) {
            actualizarChip(chip, "Sin acceso a este reporte.", false);
            return borrarSiEncolado(filaExistente);
        }
        // Unexpected status — retryable, mirrors paso-offline.js's
        // "respuesta_inesperada" fallo branch.
        var promesaInesperada = filaExistente
            ? db.adjuntos_pendientes
                  .update(filaExistente.id, { estado: "fallo", ultimoError: "respuesta_inesperada" })
                  .then(function () {
                      return filaExistente;
                  })
            : encolar(archivo, categoria, "respuesta_inesperada");
        return promesaInesperada.then(function (fila) {
            actualizarChip(chip, "No se pudo subir (respuesta inesperada).", true, function () {
                reintentarFila(fila, chip);
            });
        });
    }

    function intentarSubida(archivo, categoria, chip, filaExistente) {
        if (!navigator.onLine) {
            return encolar(archivo, categoria, "sin_conexion").then(function (fila) {
                actualizarChip(chip, "Sin conexión — pendiente de subir.", true, function () {
                    reintentarFila(fila, chip);
                });
            });
        }
        return subirAlServidor(archivo, categoria)
            .then(function (respuesta) {
                return manejarRespuesta(respuesta, chip, archivo, categoria, filaExistente);
            })
            .catch(function () {
                // Network error — queue for manual retry, never a silent
                // automatic retry (ADR-0004/S-15, same as paso-offline.js).
                return encolar(archivo, categoria, "error_de_red").then(function (fila) {
                    actualizarChip(chip, "Error de red — pendiente de subir.", true, function () {
                        reintentarFila(fila, chip);
                    });
                });
            });
    }

    function reintentarFila(fila, chip) {
        if (!fila) {
            return;
        }
        actualizarChip(chip, "Reintentando…", false);
        var intentosPrevios = typeof fila.intentos === "number" ? fila.intentos : 0;
        var incrementar = fila.id
            ? db.adjuntos_pendientes.update(fila.id, { intentos: intentosPrevios + 1 })
            : Promise.resolve();
        incrementar
            .then(function () {
                fila.intentos = intentosPrevios + 1;
                return subirAlServidor(fila.blob, fila.categoria);
            })
            .then(function (respuesta) {
                return manejarRespuesta(respuesta, chip, fila.blob, fila.categoria, fila);
            })
            .catch(function () {
                actualizarChip(chip, "Error de red — pendiente de subir.", true, function () {
                    reintentarFila(fila, chip);
                });
            });
    }

    // ---- Selection handling ---------------------------------------------------

    function manejarSeleccion(evento) {
        var archivos = Array.prototype.slice.call(evento.target.files || []);
        entrada.value = ""; // allow re-selecting the same file later
        var categoria = categoriaSeleccionada();
        archivos.forEach(function (archivoOriginal) {
            var chip = crearChip("Procesando " + (archivoOriginal.name || "adjunto") + "…");
            if (!esFormatoPermitido(archivoOriginal)) {
                actualizarChip(chip, "Formato no permitido — solo este adjunto falló.", false);
                return;
            }
            procesarArchivo(archivoOriginal)
                .then(function (archivoFinal) {
                    if (archivoFinal.size > TAMANO_MAXIMO_BYTES) {
                        // Fallback original still exceeds the ceiling (spec
                        // scenario) — block only this attachment.
                        actualizarChip(chip, "Archivo demasiado grande (>8MB) — solo este adjunto falló.", false);
                        return null;
                    }
                    return intentarSubida(archivoFinal, categoria, chip, null);
                })
                .catch(function () {
                    // Defensive: every pipeline step already catches, but
                    // never let an unexpected rejection escape unhandled.
                    actualizarChip(chip, "No se pudo procesar este adjunto.", false);
                });
        });
    }

    entrada.addEventListener("change", manejarSeleccion);

    // ---- Reconciliation on load (design's state table, mirrors
    // paso-offline.js's reconciliar()) — re-render pending/failed chips for
    // this report+section, never auto-retry (ADR-0004/S-15) -----------------

    function reconciliar() {
        db.adjuntos_pendientes
            .where("[reporteId+seccionId]")
            .equals([reporteId, seccionId])
            .toArray()
            .then(function (filas) {
                filas.forEach(function (fila) {
                    var chip = crearChip(fila.nombreOriginal || "adjunto");
                    var mensaje =
                        fila.estado === "fallo"
                            ? "No se pudo subir (" + (fila.intentos || 0) + " intentos)."
                            : "Sin conexión — pendiente de subir.";
                    actualizarChip(chip, mensaje, true, function () {
                        reintentarFila(fila, chip);
                    });
                });
            });
    }

    reconciliar();
})();
