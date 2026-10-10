# End Change

End a Change only after implementation is finished and the user gives final confirmation.

## Readiness

1. Confirm `CHANGE.md` is in `review` and every planned output exists.
2. Run the Change-completion review in `VERIFICATION.md` against the user intent, approved plan, Git diff, source, tests or structural checks, and raw results.
3. Resolve every `revision_required`, `user_decision_required`, or `unverifiable` result.
4. Push the reviewed Change branch automatically.
5. Report the result and ask once for final completion confirmation.

Do not complete a Change with failed verification, unresolved decisions, scope drift, an unowned file, or a Git conflict.

## After final confirmation

1. Update `project/PROJECT_STATUS.md` with a one-line result, archive link, version, remaining work, and one next action.
2. Set the Change state to `completed` and record the final result.
3. Move the whole folder to `archive/YYYY-MM-DD-<name>/` using the Asia/Seoul completion date. Never overwrite an existing archive.
4. Follow the commit, no-ff merge, tag, push, and branch cleanup sequence in `GIT.md`.
5. Refresh the local Project Flow.
6. Send the Telegram completion notice once.

If a later step fails, preserve the completed earlier state, record the exact failed step in the archived Handoff, and resume idempotently. Do not move the archive back to `change/` merely because merge, push, or notification failed.

## Telegram

Use the Telegram Bot API directly with environment variables `AIPF_TELEGRAM_BOT_TOKEN` and `AIPF_TELEGRAM_CHAT_ID`. Send project name, Change, result, branch/tag, and next action. Never ask for notification approval.

- Missing credentials: skip and report briefly.
- Failed request: record and report; do not undo Change completion.
- Redact secrets and sensitive inputs from the message and logs.
- Record a sent marker in the archived Handoff before retrying so the same completion is not sent twice.
- Telegram replies, polling, webhooks, and user approval through Telegram are outside scope.
