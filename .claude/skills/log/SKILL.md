---
description: View Regent activity log with step history, filtering, and formatting options. Use when reviewing agent session history, finding specific changes, or understanding what happened in previous steps.
allowed-tools: Bash(rgt log *)
argument-hint: "[filter-flags]"
---

Display the Regent activity log showing captured steps, tool calls, and conversation context.

Run the log command with any flags:
```bash
rgt log $ARGUMENTS
```

## Common usage

Show recent steps:
```bash
rgt log
```

Filter by session:
```bash
rgt log --session <session-id>
```

Change format:
```bash
rgt log --format timeline
rgt log --format compact
```