# Privacy Policy — 1min_scientist uploader

**Last updated: 2026-09-20**

`1min_scientist uploader` is a personal command-line tool used by a single
person to upload their own short-form videos to their own TikTok account.
It is not a product offered to other people and has no users other than its
operator.

Source code: <https://github.com/BudongJW/saltube>

## What this tool does

It sends video files that the operator produced to the operator's own TikTok
inbox (drafts), using TikTok's Content Posting API with the `video.upload`
scope. The operator then finishes and publishes the post inside the TikTok app.

## What data is collected

**None from anyone other than the operator.**

The tool has no server, no database, no analytics, no telemetry, and no
third-party services. It does not collect, receive, or process data about
TikTok users, viewers, or any other person.

## What is stored, and where

| Data | Where | Why |
|---|---|---|
| TikTok OAuth access token | On the operator's own computer, in a local file (`.tiktok_token.json`, permissions `0600`) | To authenticate uploads to the operator's own account |
| TikTok OAuth refresh token | Same file | To renew the access token when it expires |

Nothing is transmitted anywhere except directly to TikTok's own API endpoints
(`open.tiktokapis.com`). No copy of the token or of any uploaded video is sent
to the developer or to any third party, because there is no such destination —
the tool runs entirely on the operator's machine.

The token file is excluded from version control and is never published.

## Video content

Videos uploaded through this tool are created by the operator. They are sent
to TikTok and are then subject to TikTok's own Privacy Policy and Terms of
Service. This tool retains no copy beyond the operator's local build output.

## Sharing

No data is shared with anyone. There are no third-party recipients, no
advertising, no data sales, and no cross-service tracking.

## Retention and deletion

The token file lives on the operator's computer until deleted. Deleting the
file removes all stored data. The operator can additionally revoke this
application's access at any time from TikTok's account settings, which
invalidates the tokens regardless of whether the file still exists.

## Children

This tool is not directed at children and is not used by anyone but its
operator.

## Changes

Any change to this policy will be committed to the repository linked above,
where the full revision history is publicly visible.

## Contact

Open an issue at <https://github.com/BudongJW/saltube/issues>.
