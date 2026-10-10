# Handoff

Each active Change has one English `HANDOFF.md`. It is a current resume pointer, not a conversation transcript.

## Required form

```markdown
# Handoff

## Objective
## Git State
## Current State
## Verified Results
## Failed Attempts
## Open Issues
## Next Action
## Relevant Files
```

Record branch, HEAD, base commit, modified and untracked files, last completed work, work in progress, exact commands and observed results, failed approaches and why, unresolved decisions, one exact next action, and only the files needed to resume.

Update after a meaningful commit and before pause, interruption, blockage, or session end. Replace stale current-state text instead of accumulating a full log; retain failed approaches that prevent repeated work.

At resume, distrust the Handoff until Git state, files, recent commits, and the last important check have been inspected. Move the Handoff with its Change into `archive/`.
