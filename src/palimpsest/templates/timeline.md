# TIMELINE — {{INVESTIGATION_NAME}}

<!--
  INSTRUCTIONS FOR THE JOURNALIST

  This is a standalone timeline. It accompanies the dossier but lives in its
  own file so it can be referenced independently — useful for editors, lawyers,
  and fact-checkers who need the sequence at a glance.

  Fill in every {{PLACEHOLDER}}. Add more rows to the table as needed.
-->

**Compiled**: {{DATE_COMPILED}}
**Investigator**: {{INVESTIGATOR_NAME}}
**Part of dossier**: {{DOSSIER_FILENAME}}

---

## Overview

{{TIMELINE_INTRO_PARAGRAPH}}

<!-- 2-4 sentences. What story does this timeline tell? Why does the sequence
     matter? If there's a single "smoking gun" date, call it out here. -->

---

## Gantt Chart

<!--
  A Mermaid gantt chart gives a visual sense of pacing and overlap. Use it
  when events span months or years and the rhythm matters (e.g. "everything
  happened in Q2" or "there was an 18-month gap").
-->

```mermaid
gantt
    title {{INVESTIGATION_NAME}} — Event Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %Y-%m

    section {{SECTION_1_LABEL}}
    {{EVENT_1_LABEL}} :{{EVENT_1_ID}}, {{EVENT_1_START}}, {{EVENT_1_END}}
    {{EVENT_2_LABEL}} :{{EVENT_2_ID}}, {{EVENT_2_START}}, {{EVENT_2_END}}

    section {{SECTION_2_LABEL}}
    {{EVENT_3_LABEL}} :{{EVENT_3_ID}}, {{EVENT_3_START}}, {{EVENT_3_END}}
    {{EVENT_4_LABEL}} :{{EVENT_4_ID}}, {{EVENT_4_START}}, {{EVENT_4_END}}

    section {{SECTION_3_LABEL}}
    {{EVENT_5_LABEL}} :{{EVENT_5_ID}}, {{EVENT_5_START}}, {{EVENT_5_END}}
```

<!--
  Mermaid gantt notes:
    - dateFormat and axisFormat control how dates are displayed
    - Use milestones (": milestone, id, date") for single-day events
    - Use date ranges (": id, start, end") for periods
    - Sections group related events visually
-->

---

## Date Precision Levels

<!--
  Not every date in an investigation is equally certain. Use these labels
  consistently so no one mistakes a guess for a confirmed date.
-->

| Precision | Meaning | Example |
|---|---|---|
| **exact** | Day-accurate, independently corroborated. The source is a timestamped record, receipt, commit, legal filing, or direct observation with a reliable witness. | `2026-06-04` — phishing email sent (email headers) |
| **month** | Month is known, specific day is unconfirmed. The event is anchored to a month by at least one reliable source, but daylight granularity is lacking. | `2026-06` — SECURITY.md deleted (Git history shows month, not day) |
| **year** | Year is known, month and day are unconfirmed. Often from memory, approximate records, or events that can only be placed within a calendar year. | `2018` — subject incorporated company |
| **circa** | Best-guess window. No primary source pins it down. Usually bracketed with a rationale in the Notes column. | `circa 2019` — apartment compromised (victim's estimate, ±6 months) |

---

## Detailed Timeline

<!--
  The main event table. Every row should have a Date, a Precision label,
  a description of the Event, the Source it came from, and a Confidence
  rating (High / Medium / Low) for that specific data point.

  Sort by date ascending. Use "N/A" for empty cells rather than leaving
  them blank — it signals you checked, not that you skipped it.
-->

| # | Date | Precision | Event | Source | Confidence | Notes |
|---|---|---|---|---|---|---|
| 1 | {{DATE_1}} | {{PRECISION_1}} | {{EVENT_1}} | {{SOURCE_1}} | {{CONFIDENCE_1}} | {{NOTES_1}} |
| 2 | {{DATE_2}} | {{PRECISION_2}} | {{EVENT_2}} | {{SOURCE_2}} | {{CONFIDENCE_2}} | {{NOTES_2}} |
| 3 | {{DATE_3}} | {{PRECISION_3}} | {{EVENT_3}} | {{SOURCE_3}} | {{CONFIDENCE_3}} | {{NOTES_3}} |
| 4 | {{DATE_4}} | {{PRECISION_4}} | {{EVENT_4}} | {{SOURCE_4}} | {{CONFIDENCE_4}} | {{NOTES_4}} |
| 5 | {{DATE_5}} | {{PRECISION_5}} | {{EVENT_5}} | {{SOURCE_5}} | {{CONFIDENCE_5}} | {{NOTES_5}} |
| 6 | {{DATE_6}} | {{PRECISION_6}} | {{EVENT_6}} | {{SOURCE_6}} | {{CONFIDENCE_6}} | {{NOTES_6}} |
| 7 | {{DATE_7}} | {{PRECISION_7}} | {{EVENT_7}} | {{SOURCE_7}} | {{CONFIDENCE_7}} | {{NOTES_7}} |
| 8 | {{DATE_8}} | {{PRECISION_8}} | {{EVENT_8}} | {{SOURCE_8}} | {{CONFIDENCE_8}} | {{NOTES_8}} |
| 9 | {{DATE_9}} | {{PRECISION_9}} | {{EVENT_9}} | {{SOURCE_9}} | {{CONFIDENCE_9}} | {{NOTES_9}} |
| 10 | {{DATE_10}} | {{PRECISION_10}} | {{EVENT_10}} | {{SOURCE_10}} | {{CONFIDENCE_10}} | {{NOTES_10}} |
| 11 | {{DATE_11}} | {{PRECISION_11}} | {{EVENT_11}} | {{SOURCE_11}} | {{CONFIDENCE_11}} | {{NOTES_11}} |
| 12 | {{DATE_12}} | {{PRECISION_12}} | {{EVENT_12}} | {{SOURCE_12}} | {{CONFIDENCE_12}} | {{NOTES_12}} |
| 13 | {{DATE_13}} | {{PRECISION_13}} | {{EVENT_13}} | {{SOURCE_13}} | {{CONFIDENCE_13}} | {{NOTES_13}} |
| 14 | {{DATE_14}} | {{PRECISION_14}} | {{EVENT_14}} | {{SOURCE_14}} | {{CONFIDENCE_14}} | {{NOTES_14}} |
| 15 | {{DATE_15}} | {{PRECISION_15}} | {{EVENT_15}} | {{SOURCE_15}} | {{CONFIDENCE_15}} | {{NOTES_15}} |

<!-- Add more rows as needed. Copy and paste the template row above. -->

---

## Key Patterns

<!--
  What does the sequence reveal? Look for:
    - Clusters (multiple events in a short window)
    - Gaps (periods with no activity — are they real or just undetected?)
    - Escalation steps (did events get more serious over time?)
    - Trigger events (did something specific set off a chain?)
  Optional section — delete if not useful for your investigation.
-->

- {{PATTERN_1}}
- {{PATTERN_2}}
- {{PATTERN_3}}

---

## Sources for This Timeline

<!--
  A short index of the key sources used in the timeline. Full source index
  lives in the dossier; this is just the subset relevant here.
-->

| # | Source | Type | Location |
|---|---|---|---|
| 1 | {{SOURCE_1_NAME}} | {{SOURCE_1_TYPE}} | {{SOURCE_1_LOCATION}} |
| 2 | {{SOURCE_2_NAME}} | {{SOURCE_2_TYPE}} | {{SOURCE_2_LOCATION}} |
| 3 | {{SOURCE_3_NAME}} | {{SOURCE_3_TYPE}} | {{SOURCE_3_LOCATION}} |
| 4 | {{SOURCE_4_NAME}} | {{SOURCE_4_TYPE}} | {{SOURCE_4_LOCATION}} |
| 5 | {{SOURCE_5_NAME}} | {{SOURCE_5_TYPE}} | {{SOURCE_5_LOCATION}} |

<!-- Source types: Git commit, Email header, Public record, Witness interview,
     Photograph, Screenshot, Social media post, etc. -->
