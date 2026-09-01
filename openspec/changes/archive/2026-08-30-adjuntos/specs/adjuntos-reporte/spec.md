# Adjuntos Reporte Specification

## Purpose

Define attachment capture (`croquis`/`evidencia`, S-08) for a `Reporte`: a standalone
`Adjunto` model outside `TipoDeDato`/`ValorDeReporte`, client-side format/size
handling with per-attachment failure isolation, offline queueing through the shared
Dexie schema, and server-side storage/listing on `VercelBlobStorage`.

## Requirements

### Requirement: Standalone Adjunto Model

The system MUST define `reportes/models.py::Adjunto` as a model independent of
`TipoDeDato`/`ValorDeReporte`, with a `ForeignKey` to `Reporte`, a file field on
`VercelBlobStorage`, a category (`croquis` or `evidencia`, hardcoded to S-08), autor,
timestamps, original filename, size, and content-type.

#### Scenario: Attachment is stored independent of ValorDeReporte

- GIVEN a `Reporte` with captured field values
- WHEN an attachment is saved for S-08
- THEN it is persisted as an `Adjunto` row, not a `ValorDeReporte` row

### Requirement: Format Allowlist

The system MUST accept only JPEG, PNG, WEBP, and HEIC/HEIF content types or file
extensions, identically enforced on client and server.

#### Scenario: Server rejects a disallowed format independent of client validation

- GIVEN a request to the upload endpoint carrying a file with an unlisted content-type
- WHEN the server validates the upload
- THEN the server rejects the attachment regardless of any client-side check outcome

### Requirement: Server-Side Size Ceiling

The system MUST reject, server-side, any attachment exceeding 8MB, independent of
client-side compression outcome.

#### Scenario: Oversized file rejected after failed/skipped client compression

- GIVEN a file larger than 8MB reaches the server (client compression failed or was
  unreachable)
- WHEN the server validates the upload
- THEN the upload is rejected with a size error, and no `Adjunto` row is created

### Requirement: Per-Attachment Failure Isolation

The system MUST block only the failing attachment on validation failure; it MUST NOT
block or roll back the rest of the report/step submission.

#### Scenario: One invalid attachment does not block step submission

- GIVEN a step submission includes one valid field values payload and one oversized
  attachment
- WHEN the step is submitted
- THEN the field values are saved and the step succeeds
- AND only the oversized attachment is rejected, with an error surfaced for it alone

### Requirement: Client-Side HEIC Conversion Before Compression

When a selected file is detected as HEIC/HEIF (by content-type or extension), the
client MUST attempt conversion to JPEG via `heic2any` before running
`browser-image-compression`. Non-HEIC files MUST skip conversion and go directly to
compression.

#### Scenario: HEIC file is converted then compressed

- GIVEN a user selects a HEIC file
- WHEN the client processes it before upload
- THEN `heic2any` converts it to JPEG first, and the JPEG result is then passed to
  `browser-image-compression`

#### Scenario: Non-HEIC file skips conversion

- GIVEN a user selects a JPEG/PNG/WEBP file
- WHEN the client processes it before upload
- THEN the conversion step is skipped and the file goes directly to compression

### Requirement: Client-Side Best-Effort Compression with Fallback

The client MUST attempt compression via `browser-image-compression` before upload.
If HEIC conversion fails, compression fails, or the CDN is unreachable, the client
MUST fall back to the original file (still validated against the 8MB ceiling) rather
than blocking capture.

#### Scenario: CDN unreachable falls back to original file

- GIVEN the compression/conversion CDN libraries fail to load
- WHEN the user submits an attachment under 8MB
- THEN the original, uncompressed file is queued/uploaded without blocking capture

#### Scenario: Conversion or compression failure falls back to original file

- GIVEN `heic2any` or `browser-image-compression` throws during processing
- WHEN the client handles the failure
- THEN it falls back to the original file, subject to the 8MB ceiling, instead of
  hard-blocking the attachment

#### Scenario: Fallback original still exceeds ceiling

- GIVEN compression/conversion fails and the original file exceeds 8MB
- WHEN the client validates the fallback file
- THEN that attachment alone is blocked with an error, without blocking the rest of
  the step submission

### Requirement: Offline Queueing Through Shared Dexie Schema

The system MUST queue attachment data through the existing shared Dexie schema owned
by `reportes/static/reportes/offline-db.js` (single `.version()` owner). The system
MUST NOT introduce a second `Dexie(...)` instance. Attachment upload MUST use its own
`fetch` call to a dedicated attachment endpoint, separate from `paso-offline.js`'s
step-submission `fetch(form.action, {body: new FormData(form)})` call, so that an
attachment failure never blocks or rolls back the step's field values (per
"Per-Attachment Failure Isolation").

#### Scenario: Attachment queued and synced independently of step submission

- GIVEN a user captures an attachment while offline
- WHEN `paso-offline.js`'s companion attachment logic queues it for later sync
- THEN the attachment blob is stored in the existing shared Dexie schema (new
  store/shape added there, no second Dexie database created), and synced later via its
  own `fetch` call to the dedicated attachment upload endpoint, independent of the
  step's own field-values submission

### Requirement: No Hard Cap on Attachment Count

The system MUST NOT impose a maximum number of attachments per `Reporte`.

#### Scenario: Multiple attachments accepted for one report

- GIVEN a report already has several valid attachments
- WHEN another valid attachment is submitted
- THEN it is accepted and stored, with no count-based rejection

### Requirement: Server-Side Listing and Download

The system MUST provide a Django view to list and download a report's attachments.

#### Scenario: Authorized user lists a report's attachments

- GIVEN a `Reporte` with stored attachments
- WHEN an authorized user requests the attachment list view
- THEN the response includes each attachment's metadata and a download link
