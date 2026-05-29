# Attachment Support Design

## Overview

Add attachment support in three areas: viewing attachment metadata in threads, extracting attachments to disk, and sending emails with file attachments.

## 1. Viewing Attachments

Extend `message_to_text` in `notmuchlib.py` to list attachments after message body text.

Output format per message:
```
FROM: alice@example.com
DATE: 2024-01-25
Message content here...

ATTACHMENTS:
- report.pdf (45.2 KB)
- image.png (120.3 KB)
```

New function `get_attachments_summary(message) -> list[dict]` extracts attachment metadata (filename, size, content_type) from MIME parts. A part is considered an attachment if it has a filename OR a `Content-Disposition: attachment` header. `text/*` parts without `Content-Disposition: attachment` are skipped.

New helper `format_attachment_size(size_bytes: int) -> str` formats bytes as human-readable (KB/MB).

## 2. Extracting Attachments

New MCP tool: `extract_attachments(thread_id: str) -> str`

Iterates all messages in a thread, collects attachments, saves to `DRAFT_DIR/attachments/<thread_id>/`. A global counter prefix handles filename collisions across messages: `1_report.pdf`, `2_image.png`, `3_image.png`. Counter increments per attachment in message order.

Returns:
```
Extracted 3 attachments to /path/to/drafts/attachments/thread123/:
- 1_report.pdf (45.2 KB)
- 2_image.png (120.3 KB)
- 3_image.png (89.1 KB)
```

Implementation split for testability:
- `get_message_attachments(message) -> list[tuple[str, bytes]]` -- extracts (filename, raw data) pairs from a single message's MIME parts. Uses the same attachment detection logic as `get_attachments_summary` (filename present OR `Content-Disposition: attachment`). Falls back to `attachment_<index>` for parts with `Content-Disposition: attachment` but no filename.
- `save_attachments(attachments: list[tuple[str, bytes]], dest_dir: Path) -> list[dict]` -- writes files with counter prefixes, returns list of dicts with `path`, `filename`, `size`.

## 3. Sending Attachments

New optional parameter on `compose_new_email` and `compose_email_reply`: `attachments: Optional[List[str]]` -- list of absolute file paths.

`compose()` validates each path exists and is a file, then stores paths in `draft.json` metadata under the `attachments` key.

`send()` changes MIME structure when attachments are present:
- Without attachments (unchanged): `multipart/alternative` > `multipart/related` (HTML + inline images)
- With attachments: `multipart/mixed` > [`multipart/alternative` > `multipart/related`] + `MIMEBase` parts per attachment

Each attachment gets `Content-Disposition: attachment; filename="<name>"`. File type detected via `mimetypes.guess_type` (already imported).

## 4. Testing

### test_notmuchlib.py
- `format_attachment_size`: bytes/KB/MB formatting
- `get_attachments_summary`: needs mocked message with MIME parts; verifies correct filtering (skips text/plain, text/html without disposition; includes parts with filename or Content-Disposition: attachment)
- `save_attachments`: uses `tmp_path`, verifies counter prefixes, file content, returned metadata

### test_sendmail.py
- `compose()` with attachments: validates paths stored in draft.json, rejects nonexistent paths
- `send()` with attachments: verifies `multipart/mixed` structure, correct Content-Disposition headers, file content in MIME parts (mocked subprocess)

## Files Modified

- `notmuchlib.py` -- add `get_attachments_summary`, `get_message_attachments`, `save_attachments`, `format_attachment_size`; extend `message_to_text`
- `sendmail.py` -- add `attachments` parameter to `compose()`; extend `send()` MIME assembly
- `server.py` -- add `attachments` parameter to `compose_new_email`/`compose_email_reply`; register `extract_attachments` tool
- `tests/test_notmuchlib.py` -- new tests for attachment functions
- `tests/test_sendmail.py` -- new tests for compose/send with attachments
