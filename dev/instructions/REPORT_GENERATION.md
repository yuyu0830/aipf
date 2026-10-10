# Report Generation

Include all information the user needs, but express it with the fewest clear words.

## Order

```text
result -> problem or decision -> next action
```

- Lead with the conclusion.
- Remove greetings, previews, repetition, and irrelevant background.
- Do not omit evidence, risk, failure, uncertainty, or a needed decision merely to shorten the report.
- Put supplementary detail behind a user request, not decision-critical detail.
- Use simple Korean for user reports.

## Format

- Use a compact table for comparisons and repeated fields.
- Use pseudocode for algorithms.
- Use plain-text code blocks for formulas in chat; do not use LaTeX in chat.
- Cite an external source or local path next to the supported statement.
- Do not repeat the same content in prose and a table.

## Next action

Describe the next action in at most three short lines:

```text
다음 행동: <action>
내용: <purpose and work>
변경: <affected paths or no change>
```

Create a separate report file only when the user asks for one.
