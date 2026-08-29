# Generacion Documento Specification

## Purpose

Let any authenticated user generate and download a closed report's populated `.xlsx` document on demand, an unlimited number of times, with a durable audit trail of each successful generation. Generation failures must degrade gracefully to a flash message on the review screen, never a raw error page.

## Requirements

### Requirement: Generacion Model

The system MUST provide a `Generacion` model recording one row per successful document generation.

The model MUST have a foreign key to `Reporte`, a foreign key `usuario` to `settings.AUTH_USER_MODEL` (any authenticated user, not creator-restricted), and an auto-populated `fecha` timestamp. The model MUST NOT enforce a uniqueness constraint limiting the number of generations per report.

#### Scenario: Generacion row created on success

- GIVEN a `Reporte` with an existing `VistoBueno` and `puede_generar` True
- WHEN any authenticated user POSTs to `generar` and generation succeeds
- THEN one new `Generacion` row is created with that user and current timestamp

#### Scenario: Repeated generation creates multiple rows

- GIVEN a `Reporte` already generated once successfully
- WHEN the same or a different authenticated user POSTs to `generar` again and it succeeds
- THEN a second `Generacion` row is created
- AND no error occurs from the repeat

### Requirement: Shared Valores Helper

The system MUST provide `reportes/valores.py::valores_de_reporte(reporte)`, extracting the `{v.identificador_de_campo: v.valor ...}` construction previously duplicated in `validacion.py` and `views.py::paso`, and MUST reuse it from `generar` and from both prior call sites.

#### Scenario: Helper produces the values dict used for generation

- GIVEN a `Reporte` with captured `ValorDeReporte` rows
- WHEN `generar` builds its `valores` argument
- THEN it calls `valores_de_reporte(reporte)` rather than duplicating the dict comprehension

### Requirement: Generation Requires Prior Visto Bueno

The system MUST reject `generar` requests for a `Reporte` that has no `VistoBueno`, redirecting to `revision` without generating a document.

#### Scenario: Generation attempted before closure

- GIVEN a `Reporte` with no `VistoBueno`
- WHEN an authenticated user POSTs to `generar`
- THEN no `.xlsx` is streamed, no `Generacion` row is created, and the response redirects to `revision`

### Requirement: Any Authenticated User May Generate

The system MUST expose `generar` as a POST-only, `@login_required` view with no creator restriction: any authenticated user may generate a document for a closed report.

#### Scenario: Non-creator generates successfully

- GIVEN a `Reporte` created by user A, closed (has `VistoBueno`), `puede_generar` True
- WHEN user B (authenticated, not the creator) POSTs to `generar`
- THEN generation succeeds, a `Generacion` row is created with `usuario=B`, and the `.xlsx` is streamed to B

### Requirement: Server-Side Eligibility Re-Check on Generation

The system MUST re-validate `puede_generar` server-side inside `generar` (defense in depth), independent of client-side gating and independent of the `VistoBueno` check.

#### Scenario: Generation rejected when no longer eligible

- GIVEN a `Reporte` with a `VistoBueno` but `puede_generar` now False
- WHEN an authenticated user POSTs to `generar`
- THEN the request is rejected, no `.xlsx` is streamed, no `Generacion` row is created

### Requirement: Generation Failures Degrade to a Flash Message

The system MUST catch `ProblemaDeGeneracion` raised by `generador.generar_reporte` and redirect to `revision` with a Django messages framework error message. The system MUST NOT let generation failures surface as a raw 500 or a standalone error page.

#### Scenario: Generator raises PlantillaIlegible

- GIVEN a `Reporte` eligible for generation
- WHEN `generador.generar_reporte` raises `PlantillaIlegible`
- THEN the response redirects to `revision`
- AND a flash error message is present in the response context/session
- AND the response status is not 500

#### Scenario: Generator raises ValoresIncompletos

- GIVEN a `Reporte` eligible for generation
- WHEN `generador.generar_reporte` raises `ValoresIncompletos`
- THEN the response redirects to `revision`
- AND a flash error message is present
- AND the response status is not 500

### Requirement: Successful Generation Streams the Document

The system MUST stream the generated `.xlsx` as an `HttpResponse` with `Content-Disposition: attachment` and the correct spreadsheet `Content-Type` on success.

#### Scenario: Successful download response shape

- GIVEN a `Reporte` eligible for generation with a `VistoBueno`
- WHEN `generar` succeeds
- THEN the response has `Content-Type` for `.xlsx` and a `Content-Disposition: attachment` header with a filename
- AND the response body round-trips through `load_workbook(BytesIO(response.content))`
