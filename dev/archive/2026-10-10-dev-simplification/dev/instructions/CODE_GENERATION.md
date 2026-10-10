# Code Generation

This file defines code form, not implementation scope. Scope and behavior come from the approved `CHANGE.md`.

## Implementation size

Start with the minimum behavior requested for AIPF's solo local use. Prefer a direct command sequence over a framework, validation layer, or configurable modes. Use the underlying tool's normal failure result. Add custom error handling only for a concrete requested case.

Do not create integrity validation, hypothetical failure detection, race handling, or tests for those guards by default. Verify the changed normal behavior directly; introduce automated tests when an actual need justifies them.

## Function structure

Before creating, removing, splitting, merging, renaming, or changing the inputs or outputs of functions, present prototypes containing:

```text
name
inputs
output
responsibility
call relationship
```

Implement only after the user approves the prototypes. If an unplanned helper function becomes necessary, stop, revise the prototype set, and obtain approval. A small internal edit that does not change function structure needs no new prototype approval.

## Readability

- Keep functions and code blocks vertically short without hiding behavior.
- Use the shortest variable name that still makes its role clear.
- Prefer clear direct code over unnecessary abstraction or premature reuse.
- Keep one clear responsibility per function, but do not extract trivial one-use wrappers merely to reduce line count.
- Follow the existing language and project format. Do not install a style tool only for formatting.

## Comments

- Use comments actively at behavior boundaries.
- Prefer a short multi-line comment explaining purpose, reason, and caution.
- Do not translate every code line into a comment.
- Do not use comments to hide unclear code.
