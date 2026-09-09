# Project Workflows

## Plan

Agree on goal, scope, outputs, acceptance criteria, constraints, references, and Task order. Save only after showing the user a final preview. Do not execute before approval.

## Task

Read the active Task and its references. Create declared outputs under `src/`. Run declared verification, save evidence, and wait for user review.

## Review

- `approve`: accept the result and continue.
- `revise`: save user feedback and repeat the Task.
- `retry`: repeat the unchanged Task.
- `cancel`: cancel the Task and stop the project.

## Reference source

Store originals under `ref/` without overwriting them. Add a sidecar `*.source.yaml` with source URL, retrieval time, title, license when known, checksum, and related Task IDs.
