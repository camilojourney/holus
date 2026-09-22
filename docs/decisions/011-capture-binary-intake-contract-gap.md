# Capture binary intake contract gap

- Status: blocked pending an upstream contract
- Scope: Holus capture route v1

The current capture contract supports text plus attachment metadata only:
`POST /api/v1/capture/suggest` accepts `attachment_url`,
`attachment_filename`, and `attachment_content_type`. It classifies image and
PDF inputs and produces route suggestions. The browser file picker currently
sends only the filename and MIME type.

There is no existing Holus or Social API contract for:

- multipart or binary upload of image/PDF bytes;
- authenticated upload/storage ownership and retention;
- extraction/OCR of image/PDF content;
- an extraction job identifier/status or retry semantics;
- passing an uploaded attachment into `capture/preview` and the content queue;
- a safe preview reference for the extracted result.

Therefore this slice must not invent an upload endpoint, storage bucket, OCR
worker, queue, auth, or policy layer. Until an upstream contract specifies
those seams, the supported local behavior is metadata classification and text
preview only. Unsupported attachment metadata is rejected with HTTP 400 rather
than silently treated as text. Publishing remains outside this contract.
