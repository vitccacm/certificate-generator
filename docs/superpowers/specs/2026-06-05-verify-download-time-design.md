# Verify Page: Show Certificate Download Time

**Date:** 2026-06-05
**Status:** Approved

## Goal

The public certificate verification page (`/verify/<code>`) should show when the
certificate was downloaded, sourced from the existing download logs. Must work
for older generated certificates too.

## Decision

Show the **first** download time (earliest `DownloadLog.downloaded_at`) — i.e.
when the certificate was first issued/downloaded. Stable across re-downloads.
Display **date and time** (UTC, since timestamps are stored via
`datetime.utcnow`).

## Design (Approach A — no schema change)

1. **`app/models.py`** — add a `first_downloaded_at` property on `Participant`
   returning the earliest `downloaded_at` from its `download_logs`
   relationship, or `None` if there are no logs.
2. **`app/templates/public/verify.html`** — in the `state == 'valid'` details
   list, add a "Downloaded on" row rendering
   `participant.first_downloaded_at.strftime('%B %d, %Y at %H:%M')` + " UTC",
   wrapped in `{% if participant.first_downloaded_at %}` so the row is omitted
   when no download has occurred.
3. **No route changes** — `participant` is already passed to the template.

## Older certificates

`DownloadLog` has existed since the first commit (v1), so every download ever
made has a timestamped log row — no backfill or migration needed. Certificates
pre-dating the QR verification feature (June 2026) cannot reach the verify page
at all (no QR code, `verify_enabled` gate), so they are out of scope by
construction.

## Edge cases

- Participant with zero downloads / no log rows → property returns `None`,
  template omits the row. No broken output.
- Multiple downloads → earliest log wins (`ORDER BY downloaded_at ASC LIMIT 1`).

## Rejected alternative

Adding a `first_downloaded_at` column on `Participant` with a backfill
migration — unnecessary schema/migration overhead for a read that runs once per
captcha-gated verification (YAGNI).
