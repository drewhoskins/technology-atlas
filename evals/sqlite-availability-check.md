# Eval: sqlite3 availability + skill activation

**Purpose**: Verify the `tech-atlas` skill activates correctly, that Claude Code uses `sqlite3` to query (not the JSON seeds), and that provenance is cited verbatim.

**Why interactive**: This is the actual interviewer experience — fresh Claude Code session, no pre-loaded context. Sub-agents in our build pipeline have stricter sandbox semantics that may not reflect what interviewers see.

**Time**: 5–10 minutes.

## Setup

1. Open a **NEW** Claude Code session in `/Users/drewhoskins/tech-atlas-prototype/` (don't continue the current one — context contamination would invalidate the test).
2. Verify the project skill loaded:
   * Type `/` and look for `tech-atlas` in the skill list
3. Confirm settings recognized:
   * Settings should auto-allow `Bash(sqlite3:*)` per `.claude/settings.json`. You may still get a one-time consent prompt; accept "always allow."

## Run the eval

Ask Claude Code these prompts in order. After each one, **observe the tool calls** — that's the actual signal.

### Prompt 1 (skill activation + sqlite3 path)

```
List all the innovators of buses, sorted by year. Cite sources for each.
```

**Expected**:
* Claude invokes the `tech-atlas` skill (visible in tool calls)
* Claude runs `sqlite3 data/atlas.db "..."` with a `json_each(json_extract(data, '$.innovators'))` pattern
* Returns ~17 innovators including Pascal (1662), Baudry (1826), Otto (1876), Benz (1895), Diesel (1893)
* Each innovator cited with verbatim quoted_text + URL

**Failure modes to watch for**:
* ❌ Claude reads `data/seeds/*.json` directly via `Read` tool → SKILL.md fallback wasn't triggered, but the SQL path was bypassed (means the skill isn't being followed strictly)
* ❌ Permission prompt for `sqlite3` blocks → settings.json pattern needs adjustment
* ❌ Claude paraphrases instead of citing verbatim → skill's provenance norm not landing

### Prompt 2 (composition test)

```
Now show me only the underrecognized or obscure innovators from that list, with the source URL for each.
```

**Expected**:
* Claude composes a NEW SQL query (not just filtering in chat) — should add `WHERE json_extract(value, '$.recognition_status') IN ('underrecognized', 'obscure')` to the previous query
* Returns ~7 names: Monsieur Omnès, Beau de Rochas, Robert Thomson, L.P. Draper, Foothill Transit, Proterra founders, Netphener Omnibusgesellschaft

### Prompt 3 (computational test — the demo's #11)

```
What's the lag between the first commercial internal combustion engine and the first motorized gasoline bus?
```

**Expected**:
* Claude queries key_dates from both `component:internal_combustion_engine` and `bus:motorized_gasoline`
* Computes the year delta (Otto first working engine 1876 → Netphen motorbus 1895 = ~19 years)
* Cites sources for both endpoint dates

### Prompt 4 (epistemic-honesty test — sparse coverage)

```
Compare bus diffusion in the US vs UK vs Germany between 1900 and 1940.
```

**Expected**:
* Claude reports the gap honestly: only a few datapoints in the atlas for that window
* Does NOT pad the answer with general knowledge from training data
* Suggests the atlas could be extended

## Report back

For each of the 4 prompts, note:

| | Tool used? | Right answer? | Provenance? | Notes |
|---|---|---|---|---|
| P1 |  |  |  |  |
| P2 |  |  |  |  |
| P3 |  |  |  |  |
| P4 |  |  |  |  |

Especially for **P1**: did Claude actually run `sqlite3`, or fall back to `Read` on the seed JSONs? That's the headline signal for whether the SKILL + settings.json pre-allow are working end-to-end.

If `sqlite3` was blocked: capture the exact error message Claude reported and the tool-call args it tried. That tells us whether the pattern syntax is wrong or the sub-agent sandbox is fundamentally different.

## What I'm hoping to learn

1. Does the skill auto-load correctly from `.claude/skills/tech-atlas/SKILL.md` in a fresh session?
2. Does `.claude/settings.json` pre-allow sqlite3 without prompts?
3. Does Claude actually USE sqlite3 (the demo's whole point) vs. routing around it via Read on JSON?
4. Does provenance survive end-to-end?

Knowing #3 in particular is decisive for whether the demo's Pepsi-challenge actually demonstrates what we claim.
