# Data Collection

Collect only information needed for the user's current purpose. Every factual statement must identify its basis: external source, project path, user-provided information, AI judgment, or unverified information.

## Source rules

- Prefer user originals, then official primary sources, then reliable secondary sources.
- Open and read the source; never rely on a search-result summary.
- Record the URL, title, checked date, applicable version or date, and intended use.
- Treat multiple pages repeating one original as one source.
- Report source conflicts instead of choosing silently.
- Do not download external originals.

## Mandatory source review

Invoke the external-source review in `VERIFICATION.md` for every external source. It must independently check:

1. The source actually exists.
2. The collected statement matches the source.
3. The information is needed in the current context.

Reject nonexistent or mismatched sources. Mark inaccessible sources `확인 불가`. If review subagents are unavailable, disclose that verification could not be completed.

## Reusable knowledge

Keep Change-specific findings and citations in `CHANGE.md`. Put only likely reusable verified information in `knowledge/<topic>.md`, and add every such entry to `knowledge/INDEX.md`.

A knowledge note records the verified statement, original URL, checked date/version, attack result, defense result, usable scope, and recheck condition. Recheck volatile information before reuse.
