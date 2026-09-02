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
If HEIC conversion fails, compression fails, or a library fails to load, the client
MUST fall back to the original file (still validated against the 8MB ceiling) rather
than blocking capture.

`heic2any` and `browser-image-compression` MUST be served from this application's
own origin, never from a third-party CDN: a CDN script with no integrity check runs
arbitrary code on an authenticated capture screen, and a CDN request also fails on
exactly the first-visit-without-signal case the offline layer exists for. Both are
vendored under `static/vendor/`, with version and SHA-256 recorded in
`static/vendor/PROVENANCE.md`.

#### Scenario: A library that fails to load falls back to the original file

- GIVEN the compression/conversion libraries fail to load or are unavailable
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

### Requirement: Per-User Abuse Ceiling on Upload Rate

Distinct from "No Hard Cap on Attachment Count", which is a *product* rule and
still holds: nobody in the field is ever told they have uploaded enough photos.
This is an *abuse* rule. Every upload costs Vercel Blob storage and transfer,
billed with no ceiling, and one authenticated account can loop 8MB requests
indefinitely.

The system MUST reject an upload when the requesting user has already created
`reportes.adjuntos.SUBIDAS_MAXIMAS_POR_HORA` attachments in the preceding hour,
counted across all reports. The rejection MUST use HTTP 429 (not 400) so the
client can distinguish "retry later" from "this file is wrong".

The ceiling MUST be counted per USER, never per `Reporte`: one participant
reaching their own limit MUST NOT prevent other participants from uploading to
a shared report, which would turn an abuse control into a denial of service
against the crew.

The ceiling MUST be set far enough above real usage to be invisible in normal
work. Observed usage is ~4 attachments per user per report; the configured
value is 60 per hour.

#### Scenario: Normal field usage never reaches the ceiling

- GIVEN a user uploading attachments at a realistic pace for one report
- WHEN they submit several valid attachments in a row
- THEN every one is accepted, with no rate-based rejection

#### Scenario: Upload past the hourly ceiling is rejected

- GIVEN a user who has already created `SUBIDAS_MAXIMAS_POR_HORA` attachments within the last hour
- WHEN they submit another valid attachment
- THEN the response is HTTP 429 with error id `demasiadas-subidas`, and no `Adjunto` row is created

#### Scenario: One participant's ceiling does not block another

- GIVEN participant B has reached the ceiling on a shared report
- WHEN creator A submits a valid attachment to that same report
- THEN it is accepted

### Requirement: Metadata Stripping Before Storage

A stored attachment is served from a public, permanent Vercel Blob URL: the
listing is access-scoped, the file itself is not. Whatever a phone camera
embedded therefore leaves the application readable by anyone holding the link.

The system MUST strip embedded metadata — EXIF including the GPS sub-IFD —
from every attachment it can decode, BEFORE writing it to storage. Stripping
MUST run after format/size validation, so a rejected upload costs no work.

Stripping MUST NOT degrade the image: a JPEG MUST be re-encoded reusing its
original quantization tables so decoded pixels are unchanged, PNG is lossless
by definition, and WEBP MUST be written lossless.

Stripping MUST NOT become a new way for an upload to fail. When the file
cannot be decoded, its format is not re-encodable, or the result would exceed
the size ceiling, the system MUST store the ORIGINAL file unchanged rather
than raising — mirroring the "skip, never block" posture of attachment
embedding during generation.

KNOWN LIMIT: the deployed Pillow build ships no HEIF codec, so an unconverted
HEIC/HEIF attachment cannot be decoded and retains its metadata, GPS included.
Client-side conversion to JPEG normally prevents this, but it is best-effort
and the server MUST NOT rely on it.

This requirement reduces what the public URL exposes. It does NOT make the URL
private; that remains an open architectural question.

#### Scenario: GPS coordinates are removed from an uploaded photo

- GIVEN a JPEG carrying EXIF GPS coordinates, camera make and a timestamp
- WHEN it is uploaded through the attachment endpoint
- THEN the stored file carries no EXIF block and no GPS sub-IFD

#### Scenario: Stripping preserves the photograph

- GIVEN a JPEG attachment
- WHEN its metadata is stripped
- THEN the stored image has identical dimensions, mode and decoded pixels

#### Scenario: Undecodable file is stored unchanged instead of failing

- GIVEN an attachment the image library cannot decode
- WHEN it is uploaded
- THEN the original bytes are stored, the upload succeeds, and no error is raised

### Requirement: Attachment Files Deleted When a Report Is Deleted

`Reporte` deletion is deliberately a SOFT delete: every related row, `Adjunto`
included, survives for audit and recovery. Attachment BYTES are a separate
question — they live at a public, permanent URL that no session check guards,
so leaving them behind means a report its creator deleted stays readable
forever by anyone holding the link, including someone whose access was revoked.

The system MUST delete the stored file behind every `Adjunto` of a deleted
`Reporte`, while KEEPING the `Adjunto` rows so the audit trail still records
who uploaded what and when.

Deletion MUST be attempted per attachment and MUST NOT be transactional: a
storage backend failing on one file MUST NOT abort the deletion the user asked
for, nor leave the remaining files behind. A failure MUST be logged so an
orphaned blob can be cleaned up out of band.

#### Scenario: Deleting a report removes its attachment files but keeps the rows

- GIVEN a report with a stored attachment
- WHEN its creator deletes the report
- THEN the report is marked deleted, the `Adjunto` row still exists, and the stored file no longer exists

### Requirement: Server-Side Listing and Download

The system MUST provide a Django view to list and download a report's attachments.

#### Scenario: Authorized user lists a report's attachments

- GIVEN a `Reporte` with stored attachments
- WHEN an authorized user requests the attachment list view
- THEN the response includes each attachment's metadata and a download link

### Requirement: Attachment Deletion by Creator or Uploader

The system MUST provide a POST-only view letting someone undo a mistaken
upload without a support request. Access MUST be scoped like every other
mutating action on an accessible `Reporte`, plus a second, narrower check:
only the `Reporte`'s creator or the `Adjunto`'s own `autor` may delete it.

An invited participant MUST NOT be able to delete a file a *different*
participant uploaded — this mirrors the "widen access to view, keep mutation
narrow" pattern used by `cierre-reporte`. A denied request MUST 404 rather
than reveal the attachment's existence.

Deletion MUST be a hard delete of both the stored file and the `Adjunto`
row — unlike `Reporte`, attachments carry no audit-trail requirement, so
there is no soft-delete column to set.

After deleting, the view MUST redirect back to the screen the request came
from: the standalone attachment list when the request says so, otherwise the
wizard's attachment step.

#### Scenario: Uploader deletes their own attachment

- GIVEN an `Adjunto` uploaded by invited participant B on a report created by A
- WHEN B POSTs to the delete route for that attachment
- THEN both the stored file and the `Adjunto` row are removed
- AND a success flash message is shown

#### Scenario: Creator deletes any attachment on their report

- GIVEN an `Adjunto` uploaded by invited participant B on a report created by A
- WHEN A POSTs to the delete route for that attachment
- THEN the attachment is deleted

#### Scenario: Participant cannot delete another participant's attachment

- GIVEN an `Adjunto` uploaded by participant B on a report created by A, with participant C also invited
- WHEN C POSTs to the delete route for that attachment
- THEN the response is 404 and the `Adjunto` still exists

#### Scenario: User without report access cannot delete

- GIVEN an `Adjunto` on a report user D can neither create nor was invited to
- WHEN D POSTs to the delete route
- THEN the response is 404 and the `Adjunto` still exists
