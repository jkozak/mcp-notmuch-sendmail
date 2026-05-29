# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

MCP server that connects Claude Desktop to a notmuch email database. Provides tools to search/view email threads, compose emails in markdown (rendered to HTML with LaTeX styling), and send via `sendmail`. Published to PyPI as `mcp-notmuch-sendmail`.

## Development

Python 3.10 required. Uses `uv` for package management.

```bash
uv sync                  # install dependencies
uv run mcp-notmuch-sendmail  # run the server locally
```

Publishing (requires `$PYPI_TOKEN_PROD` / `$PYPI_TOKEN_TEST` env vars):
```bash
make publish-prod        # build, publish to PyPI, commit version bump, push
make publish-test        # build, publish to test PyPI, revert version changes
```

Testing (requires `libnotmuch.so` via nix-shell):
```bash
nix-shell --run 'uv run pytest'          # run all tests
nix-shell --run 'uv run pytest -k foo'   # run matching tests
```

No linter configured.

## Required Environment Variables

- `NOTMUCH_DATABASE_PATH` - path to notmuch database
- `NOTMUCH_REPLY_SEPARATORS` - pipe-separated reply detection markers
- `SENDMAIL_FROM_EMAIL` - sender email address

Optional: `SENDMAIL_EMAIL_SIGNATURE_HTML`, `NOTMUCH_SYNC_SCRIPT`, `LOG_FILE_PATH`, `DRAFT_DIR`

## Architecture

Entry point: `server.py:main()` creates a `FastMCP` server and registers MCP tools.

Four modules under `mcp_notmuch_sendmail/`:

- **`core.py`** - shared config (env vars, constants), logging decorator (`@log`)
- **`server.py`** - MCP tool definitions; thin wrappers that delegate to `notmuchlib` and `sendmail`
- **`notmuchlib.py`** - notmuch database queries (find threads, view threads, get thread info for reply headers, sync)
- **`sendmail.py`** - email composition pipeline: markdown -> HTML (via markdown-it + Jinja2 templates) -> MIME message -> `sendmail -t`

Draft workflow: `compose()` writes `draft.md`, `draft.html`, `draft.json` to `DRAFT_DIR`. `send()` reads those files, rebuilds the MIME message, and pipes to sendmail.

Templates: `email_template.j2` (sent emails), `email_template_draft.j2` (draft preview). Styling via `latex.css`.
