# 26 — Open Issues (Markdown Ledger)

**Document status:** Tracker-blocked fallback per [`docs/25 §7`](../25_Issue_Standards.md). Each file in this directory mirrors the body of a would-be GitHub Issue so the `issue-maintainer` agent can ingest it mechanically when `gh` (or a `$GITHUB_TOKEN` API path) becomes available. The "live" issue tracker for this project is GitHub Issues on `ClaudiousAI/AutomataIQ`; this ledger is the offline shadow.

## Conventions

| Field | Source |
|---|---|
| Label taxonomy | `docs/25 §3` (type / priority / area / status) |
| Body templates | `docs/25 §6` (bug / feat / epic / chore / docs) |
| Title convention | `docs/25 §5` (conventional-commit-aligned lowercase) |
| AC checkbox ledger | `docs/25 §8` (flipped at merge-time per criterion) |
| Sub-issue linking | `docs/25 §7` (native when tracker is available; placeholder list in this ledger until mirror) |

## File naming

`<NNN>-<slug>.md` where `NNN` is a 3-digit, zero-padded, project-local ID (assigned at filing time, monotonic). The first entry in this directory is `001-m03b-storage-substrate.md` — **local ID 001, NOT a GitHub issue number.** The mirror operation (§Mirror) will create the GitHub Issue and back-fill the GH number into the file's front matter.

## File front matter (required)

Every file in this directory carries the following at the top so the `issue-maintainer` can ingest it without re-reading `docs/25`:

```yaml
---
gh_issue_number: null          # back-filled by the mirror operation when gh lands
gh_issue_url: null             # back-filled by the mirror operation
local_id: NNN                  # 3-digit, zero-padded
type: feat | bug | epic | chore | docs
priority: critical | high | medium | low
area: [backend, data, ...]     # smallest correct set per docs/25 §3.3, §4
title: "feat(<area>): <one-line>"
module: M-NN                   # per docs/22 §5
rtm_ids: [FR-NNN, NFR-NNN]     # per docs/16
filed: YYYY-MM-DD
filed_by: <handle or "orchestrator">
status: open | in-review | blocked | needs-info | closed
parent_local_id: null          # for sub-issues, the epic's local_id
sub_issue_local_ids: []        # for epics, the local_ids of the sub-issues
mirror_pending: true | false   # true until the gh mirror runs
---
```

## Mirror operation (when `gh` lands)

The `issue-maintainer` agent runs once with the directive *"mirror `docs/26_Open_Issues/` to GitHub Issues"*. For each file:

1. Read the front matter. If `mirror_pending: false`, skip.
2. If `gh_issue_number: null`, file a new GitHub Issue with the body, applying the labels from the front matter via `gh issue create --label "type:…,priority:…,area:…"` and the title verbatim.
3. For epic files with non-empty `sub_issue_local_ids`, use `gh issue create --parent <gh_issue_number>` when creating the sub-issues.
4. After the GH issue exists, set `gh_issue_number`, `gh_issue_url`, and `mirror_pending: false` in the file's front matter. Commit the change on `main` as `chore(26): mirror to GitHub Issues (#<gh_issue_number>)`.
5. Update each sub-issue's `parent_gh_issue_number` to the epic's `gh_issue_number`.

The ledger and the tracker converge; future operations use the tracker natively per `docs/25 §7` default.

## When this directory becomes empty

The directory is empty when every entry has been mirrored AND the GitHub tracker is the system of record. The `issue-maintainer` keeps the file for audit (it remains the source of the original body) but the body edits and AC checkbox flips go to the GitHub Issue thereafter. The `mirror_pending: false` field is the marker.
