# Delta for Generación de Reporte Excel

## ADDED Requirements

### Requirement: Attachment Embedding via Anchor Slots

When a `DefinicionDeTipo`'s template declares attachment anchor slots (up to 4, named
in the template YAML, mirroring the existing scalar `celda` anchor declaration), the
system MUST embed each of the report's stored `Adjunto` images into the corresponding
anchor slot via a new `generador.py::_incrustar_adjuntos` primitive, run alongside
`_intercambiar_logo` and before returning the generated workbook. This primitive is a
generalization of, not a reuse of, `_intercambiar_logo`'s single-fixed-anchor
mechanism.

#### Scenario: Attachments within anchor-slot count are embedded

- GIVEN a `Reporte` with 3 stored attachments and a template declaring 4 anchor slots
- WHEN `generar_reporte(definicion, valores)` is called
- THEN each of the 3 attachments is embedded as an image at its corresponding anchor
  slot in the exported sheet

#### Scenario: Attachments beyond anchor-slot count remain stored, not embedded

- GIVEN a `Reporte` with 6 stored attachments and a template declaring 4 anchor slots
- WHEN `generar_reporte(definicion, valores)` is called
- THEN only 4 attachments are embedded into the `.xlsx`
- AND the remaining 2 attachments stay stored and listable via the server-side
  attachment view, without raising an error

#### Scenario: No attachments leaves anchor slots empty

- GIVEN a `Reporte` with no stored attachments and a template declaring anchor slots
- WHEN `generar_reporte(definicion, valores)` is called
- THEN the exported sheet's anchor slots contain no embedded attachment images, and
  generation succeeds normally

#### Scenario: Template without declared anchor slots skips embedding entirely

- GIVEN a `DefinicionDeTipo` whose template declares no attachment anchor slots
- WHEN `generar_reporte(definicion, valores)` is called for a `Reporte` with stored
  attachments
- THEN `_incrustar_adjuntos` performs no embedding, and generation proceeds as before
  this change (cell values and logo swap only)
