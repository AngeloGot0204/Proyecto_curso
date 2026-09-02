/**
 * Client-side layer for the `paso` wizard step (backlog
 * `validacion-datos-formulario`, Phase 5; design's "`paso.js` behaviour"
 * subsection; spec `wizard-captura`: "Client-side hora range feedback",
 * "\"No cumple\" observación toggling").
 *
 * Vanilla JS only — no library, no build step (ADR-0001). No JS test
 * runner exists in this project; coverage is the rendered-attribute
 * contract this script depends on (`data-rango`, `data-rango-extremo`,
 * `data-requiere-observacion`, `data-observacion-de`, `data-campo`,
 * `data-siguiente`), asserted in `reportes/tests/test_views.py`.
 */
(function () {
    "use strict";

    var VALOR_NO_CUMPLE = "No cumple";
    var MENSAJE_RANGO_INVALIDO = "La hora de fin debe ser posterior a la hora de inicio.";

    function grupoDeCamposDeRango() {
        var entradas = Array.prototype.slice.call(
            document.querySelectorAll("[data-rango]")
        );
        var grupos = {};
        entradas.forEach(function (entrada) {
            var id = entrada.getAttribute("data-rango");
            if (!grupos[id]) {
                grupos[id] = {};
            }
            var extremo = entrada.getAttribute("data-rango-extremo");
            grupos[id][extremo] = entrada;
        });
        return grupos;
    }

    function mensajeDeAlertaPara(entradaFin) {
        var idMensaje = entradaFin.id
            ? entradaFin.id + "_mensaje_rango"
            : null;
        var mensaje = idMensaje ? document.getElementById(idMensaje) : null;
        if (mensaje) {
            return mensaje;
        }
        mensaje = document.createElement("span");
        mensaje.setAttribute("role", "alert");
        mensaje.textContent = MENSAJE_RANGO_INVALIDO;
        if (idMensaje) {
            mensaje.id = idMensaje;
        }
        entradaFin.insertAdjacentElement("afterend", mensaje);
        return mensaje;
    }

    function limpiarAlertaDeRango(entradaFin) {
        var idMensaje = entradaFin.id ? entradaFin.id + "_mensaje_rango" : null;
        var mensaje = idMensaje ? document.getElementById(idMensaje) : null;
        if (mensaje) {
            mensaje.remove();
        }
        entradaFin.removeAttribute("aria-invalid");
    }

    function aplicarEstadoDeNavegacion(habilitar) {
        // Scoped to the step's own form, never `form button[...]`: the
        // sidebar renders a logout <form> before the page content, so the
        // unscoped lookup resolved to "Cerrar sesión" — disabling logout
        // while leaving "Guardar y continuar" enabled, which quietly turned
        // this validation guard into a no-op. Same
        // `[data-reporte-id][data-seccion-id]` contract paso-offline.js
        // keys on.
        var boton = document.querySelector(
            'form[data-reporte-id][data-seccion-id] button[type="submit"]'
        );
        if (boton) {
            boton.disabled = !habilitar;
        }
        var siguiente = document.querySelector("[data-siguiente]");
        if (siguiente) {
            if (habilitar) {
                siguiente.removeAttribute("aria-disabled");
            } else {
                siguiente.setAttribute("aria-disabled", "true");
            }
        }
    }

    function evaluarRangosDeHora() {
        var grupos = grupoDeCamposDeRango();
        var algunoInvalido = false;

        Object.keys(grupos).forEach(function (id) {
            var par = grupos[id];
            var inicio = par.inicio;
            var fin = par.fin;
            if (!inicio || !fin) {
                return;
            }
            var valorInicio = inicio.value;
            var valorFin = fin.value;
            var invalido =
                valorInicio !== "" && valorFin !== "" && valorFin <= valorInicio;

            if (invalido) {
                algunoInvalido = true;
                fin.setAttribute("aria-invalid", "true");
                mensajeDeAlertaPara(fin);
            } else {
                limpiarAlertaDeRango(fin);
            }
        });

        aplicarEstadoDeNavegacion(!algunoInvalido);
        return algunoInvalido;
    }

    function aplicarToggleDeObservacion(select) {
        var claveCampo = select.getAttribute("data-requiere-observacion");
        if (!claveCampo) {
            return;
        }
        var contenedor = document.querySelector(
            '[data-campo="' + claveCampo + '"]'
        );
        if (!contenedor) {
            return;
        }
        var entrada = contenedor.querySelector(
            '[data-observacion-de="' + select.name + '"]'
        );

        var requiereObservacion = select.value === VALOR_NO_CUMPLE;

        if (requiereObservacion) {
            contenedor.hidden = false;
            if (entrada) {
                entrada.required = true;
            }
        } else {
            contenedor.hidden = true;
            if (entrada) {
                // A hidden `required` input would silently block native form
                // submission (design's explicit callout) — always strip it.
                entrada.required = false;
                entrada.value = "";
            }
        }
    }

    function evaluarTogglesDeObservacion() {
        var selects = document.querySelectorAll("[data-requiere-observacion]");
        Array.prototype.forEach.call(selects, aplicarToggleDeObservacion);
    }

    function inicializarPreventDefaultDeSiguiente() {
        var siguiente = document.querySelector("[data-siguiente]");
        if (!siguiente) {
            return;
        }
        siguiente.addEventListener("click", function (evento) {
            if (siguiente.getAttribute("aria-disabled") === "true") {
                evento.preventDefault();
            }
        });
    }

    function inicializar() {
        evaluarRangosDeHora();
        evaluarTogglesDeObservacion();
        inicializarPreventDefaultDeSiguiente();

        Array.prototype.forEach.call(
            document.querySelectorAll("[data-rango]"),
            function (entrada) {
                entrada.addEventListener("input", evaluarRangosDeHora);
                entrada.addEventListener("change", evaluarRangosDeHora);
            }
        );

        Array.prototype.forEach.call(
            document.querySelectorAll("[data-requiere-observacion]"),
            function (select) {
                select.addEventListener("change", function () {
                    aplicarToggleDeObservacion(select);
                });
            }
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", inicializar);
    } else {
        inicializar();
    }
})();
