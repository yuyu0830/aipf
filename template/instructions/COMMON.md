# Common Rules

Apply these rules to every action.

## Intent and ambiguity

- Treat any ambiguity as unresolved. Inspect relevant context, then ask the user.
- Do not infer goal, scope, outputs, ownership, or acceptance criteria from convenience.
- Prefer a slower accurate result over a fast self-directed interpretation.
- Preserve the user's overall project intent when handling a local request. Report conflicts instead of silently choosing one.

## Scope and authority

- Work only within the user's stated purpose and approved Change scope.
- Report unrelated improvements; do not implement them.
- A response to a question is information, not permission to execute.
- Begin implementation only after an explicit start instruction.
- Preserve user changes and never overwrite work with unclear ownership.

## Explanation

Explain motivation and derivation before procedure:

```text
why it matters -> governing principle -> conclusion -> procedure when needed
```

Use procedural-first explanation only when the user asks for steps or immediate operation.

## Language

- Use simple Korean for user-facing documents and reports.
- Use English for agent instructions and Handoffs.
- Keep necessary project terms; explain an uncommon technical term once.

## Safety

- Confirm destructive, irreversible, costly, or externally impactful actions unless a standing instruction explicitly authorizes them.
- Never store credentials or secrets in project files.
- Never report an unverified result as successful.
