# Project Workflows

## Plan

Agree on goal, scope, outputs, acceptance criteria, constraints, references, and Task order. Save only after showing the user a final preview. Do not execute before approval.

## Task

Read the active Task and its references. Create declared outputs under `src/`. Run declared verification, record every follow-up item in Task `remaining`, create a new immutable Evidence object for the submission, and wait for user review.

## Review

- `approve`: accept the result and continue.
- `revise`: save user feedback and repeat the Task.
- `retry`: repeat the unchanged Task.
- `cancel`: cancel the Task and stop the project.

## Checkpoint

At each Plan-agent-defined execution boundary, create one checkpoint for every participating Task. Task outputs are included from their declarations; list any additional execution paths explicitly. Checkpoint creation must stop if the Git staging area already contains changes or if another working-tree change has no confirmed owner.

Restore only from a clean working tree and only by a recorded checkpoint ID. A restore recreates that checkpoint state in a new commit, preserves the checkpoint index and append-only Evidence and Audit history, and records the restoration reason in a new Audit. Do not use destructive Git history rewriting.

## Project flow projection

`PROJECT_FLOW.md` is a read-only projection of Plans, checkpoints, material Audits, and the current runtime position. It intentionally excludes Task and Evidence detail. The AIPF CLI refreshes only the generated region between its markers; preserve content outside the markers and never edit the generated region directly. Use normal CLI state-changing commands or `status` to refresh the projection.

## Reference source

Store originals under `ref/` without overwriting them. Add a sidecar `*.source.yaml` with source URL, retrieval time, title, license when known, checksum, and related Task IDs.
