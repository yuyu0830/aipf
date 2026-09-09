# Project Workflows

This file defines the small set of reusable workflows supported by the framework. It is not an automatic planning system.

## Agree on a plan

1. Discuss the goal, scope, exclusions, outputs, acceptance criteria, constraints, references, and task order with the user.
2. Present a concise plan preview.
3. Revise the preview until the user explicitly agrees.
4. Save the plan and tasks.
5. Set the project state to `awaiting_plan_confirmation`.
6. Do not execute a task before approval.

## Execute a task

1. Read the active task and its referenced files.
2. Confirm that required inputs exist.
3. Set the task state to `running`.
4. Create or modify only declared outputs under `src/` and managed metadata under `.aipf/`.
5. Run the declared verification.
6. Save the result and evidence.
7. Set the project state to `awaiting_task_confirmation`.

## Handle user review

Record the user's decision in an audit entry.

- `approve`: complete the task and select the next task.
- `revise`: update the task contract before another run.
- `retry`: run the same task again with the existing contract.
- `cancel`: cancel the task and stop dependent project work.

The framework does not make the final acceptance decision for the user.

## Manage reference sources

1. Store external originals under `ref/`.
2. Do not overwrite an existing original.
3. Record source URL, retrieval time, title, license when known, and checksum in a sidecar `*.source.yaml` file.
4. Link task inputs directly to the source path.
5. Put derived or transformed output under `src/`.

## Send notifications

Read notification conditions from `PROJECT.md`. Supported conditions are `task_completed`, `plan_completed`, `blocked`, and `never`. Read Telegram credentials only from environment variables. Notification failure must not change project state.
