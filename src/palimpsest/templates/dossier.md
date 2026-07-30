# DOSSIER — {{INVESTIGATION_NAME}}

<!--
  INSTRUCTIONS FOR THE JOURNALIST

  Fill in every {{PLACEHOLDER}}. If a section doesn't apply, keep it and mark
  "N/A" rather than deleting it — gaps are themselves evidence of what you
  haven't found yet.

  Keep the HTML comments as you go; they explain the structure to anyone
  inheriting the dossier later. When you're done, strip the comments for the
  final handover copy if desired.

  File naming convention: {{INVESTIGATION_SLUG}}-dossier.md
-->

**Subtitle**: {{SUBTITLE}}

**Compiled**: {{DATE_COMPILED}} — Updated {{DATE_UPDATED}}
**Investigator**: {{INVESTIGATOR_NAME}}
**Evidence package**: {{EVIDENCE_DIRECTORY}}

---

## EXECUTIVE SUMMARY

<!-- 3–5 sentences. What happened, who did it, how confident are you, why
     should anyone care. Write this last, after you have everything else. -->

{{EXECUTIVE_SUMMARY_PARAGRAPH_1}}

{{EXECUTIVE_SUMMARY_PARAGRAPH_2}}

{{EXECUTIVE_SUMMARY_PARAGRAPH_3}}

---

## THE PLAYERS

<!-- For each key person, copy the block below and fill it in. Order by
     significance to the investigation, not alphabetically. -->

### {{PERSON_1_NAME}} — {{PERSON_1_ROLE_LABEL}}

| Detail | Source |
|---|---|
| Full name | {{PERSON_1_FULL_NAME}} |
| Role | {{PERSON_1_ROLE}} |
| Organisation(s) | {{PERSON_1_ORGS}} |
| Nationality | {{PERSON_1_NATIONALITY}} |
| Born | {{PERSON_1_DOB}} (age {{PERSON_1_AGE}}) |
| Location | {{PERSON_1_LOCATION}} |
| Known aliases | {{PERSON_1_ALIASES}} |
| Verified affiliations | {{PERSON_1_AFFILIATIONS}} |

**Verified via**: {{PERSON_1_VERIFICATION_SOURCES}}

**Confidence**: {{PERSON_1_CONFIDENCE_HIGH/MEDIUM/LOW}}
<!-- Explain the confidence level: what's solid and what's still shaky. -->

**Open questions**: {{PERSON_1_OPEN_QUESTIONS}}

---

### {{PERSON_2_NAME}} — {{PERSON_2_ROLE_LABEL}}

| Detail | Source |
|---|---|
| Full name | {{PERSON_2_FULL_NAME}} |
| Role | {{PERSON_2_ROLE}} |
| Organisation(s) | {{PERSON_2_ORGS}} |
| Nationality | {{PERSON_2_NATIONALITY}} |
| Born | {{PERSON_2_DOB}} (age {{PERSON_2_AGE}}) |
| Location | {{PERSON_2_LOCATION}} |
| Known aliases | {{PERSON_2_ALIASES}} |
| Verified affiliations | {{PERSON_2_AFFILIATIONS}} |

**Verified via**: {{PERSON_2_VERIFICATION_SOURCES}}

**Confidence**: {{PERSON_2_CONFIDENCE_HIGH/MEDIUM/LOW}}

**Open questions**: {{PERSON_2_OPEN_QUESTIONS}}

<!-- Add more player blocks as needed. Duplicate the section above. -->

---

## TIMELINE

<!-- Key dates only. The full timeline lives in its own file
     ({{TIMELINE_FILENAME}}) — this is the abbreviated version for
     a quick-read overview. -->

| Date | Date Precision | Event | Source | Confidence |
|---|---|---|---|---|
| {{DATE_1}} | {{PRECISION_1}} | {{EVENT_1}} | {{SOURCE_1}} | {{CONFIDENCE_1}} |
| {{DATE_2}} | {{PRECISION_2}} | {{EVENT_2}} | {{SOURCE_2}} | {{CONFIDENCE_2}} |
| {{DATE_3}} | {{PRECISION_3}} | {{EVENT_3}} | {{SOURCE_3}} | {{CONFIDENCE_3}} |
| {{DATE_4}} | {{PRECISION_4}} | {{EVENT_4}} | {{SOURCE_4}} | {{CONFIDENCE_4}} |

<!--
  Date Precision levels:
    exact   — day-accurate, corroborated (e.g. a commit timestamp, receipt)
    month   — known month, specific day unconfirmed
    year    — known year only
    circa   — best-guess window ("around 2019")
-->

**See full timeline**: {{TIMELINE_FILENAME}}

---

## EVIDENCE (VERIFIED FACTS)

<!--
  Numbered list. Each entry is something you can prove right now. Inline
  citations linking to the Source Index by number — e.g. [1][3].
  If it's not provable, it goes in Inferred below.
-->

1. {{VERIFIED_FACT_1}} [{{SOURCE_INDEX_REF}}]
2. {{VERIFIED_FACT_2}} [{{SOURCE_INDEX_REF}}]
3. {{VERIFIED_FACT_3}} [{{SOURCE_INDEX_REF}}]
4. {{VERIFIED_FACT_4}} [{{SOURCE_INDEX_REF}}]
5. {{VERIFIED_FACT_5}} [{{SOURCE_INDEX_REF}}]
6. {{VERIFIED_FACT_6}} [{{SOURCE_INDEX_REF}}]
7. {{VERIFIED_FACT_7}} [{{SOURCE_INDEX_REF}}]
8. {{VERIFIED_FACT_8}} [{{SOURCE_INDEX_REF}}]
9. {{VERIFIED_FACT_9}} [{{SOURCE_INDEX_REF}}]
10. {{VERIFIED_FACT_10}} [{{SOURCE_INDEX_REF}}]

<!-- Add more as needed. Renumber when you insert. -->

---

## INFERRED (PLAUSIBLE BUT UNPROVEN)

<!--
  Numbered list. Each inference includes:
    - What you suspect
    - Why it's plausible (the reasoning chain)
    - What evidence is missing to confirm it
  This is the honesty section — it's where you show your working.
-->

1. **{{INFERRED_CLAIM_1}}**
   - **Reasoning**: {{INFERRED_REASONING_1}}
   - **Missing evidence**: {{INFERRED_MISSING_EVIDENCE_1}}
   - **Confidence**: {{INFERRED_CONFIDENCE_1}}

2. **{{INFERRED_CLAIM_2}}**
   - **Reasoning**: {{INFERRED_REASONING_2}}
   - **Missing evidence**: {{INFERRED_MISSING_EVIDENCE_2}}
   - **Confidence**: {{INFERRED_CONFIDENCE_2}}

3. **{{INFERRED_CLAIM_3}}**
   - **Reasoning**: {{INFERRED_REASONING_3}}
   - **Missing evidence**: {{INFERRED_MISSING_EVIDENCE_3}}
   - **Confidence**: {{INFERRED_CONFIDENCE_3}}

<!-- Mark inferences that become provable as "UPGRADED TO VERIFIED" and move
     them to the Evidence section in the next update cycle. -->

---

## NETWORK MAP

<!--
  Insert a Mermaid graph showing relationships between all key entities.
  See network-map.md for a full standalone version with legend.

  Quick reference for common relation types:
    solid line (---)     = confirmed direct relationship
    dashed line (-.-)    = inferred/plausible relationship
    thick line (===)     = known institutional affiliation
    arrow (--> or -.->)  = direction of influence or reporting
-->

```mermaid
graph TD
    {{MERMAID_GRAPH_PLACEHOLDER}}
```

**Full network map with legend**: {{NETWORK_MAP_FILENAME}}

---

## SOURCE INDEX

<!--
  Numbered list of every source URL, with access date. This is your audit
  trail. If a source goes offline, you still have the reference.
-->

| # | Source | URL | Accessed |
|---|---|---|---|
| 1 | {{SOURCE_1_NAME}} | {{SOURCE_1_URL}} | {{SOURCE_1_DATE}} |
| 2 | {{SOURCE_2_NAME}} | {{SOURCE_2_URL}} | {{SOURCE_2_DATE}} |
| 3 | {{SOURCE_3_NAME}} | {{SOURCE_3_URL}} | {{SOURCE_3_DATE}} |
| 4 | {{SOURCE_4_NAME}} | {{SOURCE_4_URL}} | {{SOURCE_4_DATE}} |
| 5 | {{SOURCE_5_NAME}} | {{SOURCE_5_URL}} | {{SOURCE_5_DATE}} |
| 6 | {{SOURCE_6_NAME}} | {{SOURCE_6_URL}} | {{SOURCE_6_DATE}} |
| 7 | {{SOURCE_7_NAME}} | {{SOURCE_7_URL}} | {{SOURCE_7_DATE}} |
| 8 | {{SOURCE_8_NAME}} | {{SOURCE_8_URL}} | {{SOURCE_8_DATE}} |
| 9 | {{SOURCE_9_NAME}} | {{SOURCE_9_URL}} | {{SOURCE_9_DATE}} |
| 10 | {{SOURCE_10_NAME}} | {{SOURCE_10_URL}} | {{SOURCE_10_DATE}} |

<!--
  Archived copies: if a source is likely to disappear, archive it at
  archive.org and add a second URL column for the snapshot.
-->

---

## GAP ANALYSIS

<!--
  Bullet points. What don't you know yet? What would you go looking for if
  you had more time, money, or legal authority?
-->

- {{GAP_1}}
- {{GAP_2}}
- {{GAP_3}}
- {{GAP_4}}
- {{GAP_5}}

### Leads not yet pursued

- {{LEAD_1}}
- {{LEAD_2}}
- {{LEAD_3}}

### Evidence that could exist but hasn't been found

- {{MISSING_EVIDENCE_1}}
- {{MISSING_EVIDENCE_2}}

---

## VERIFICATION PATHS

<!--
  How an editor, lawyer, or second journalist can independently confirm your
  key facts. Separate into what anyone can do right now vs. what requires
  legal process.
-->

### Anyone can verify today (no special access needed)

1. {{VERIFICATION_STEP_1}}
2. {{VERIFICATION_STEP_2}}
3. {{VERIFICATION_STEP_3}}
4. {{VERIFICATION_STEP_4}}
5. {{VERIFICATION_STEP_5}}

### Requires legal process

- {{LEGAL_VERIFICATION_1}}
- {{LEGAL_VERIFICATION_2}}
- {{LEGAL_VERIFICATION_3}}

### Requires specialist access

- {{SPECIALIST_VERIFICATION_1}}
- {{SPECIALIST_VERIFICATION_2}}

---

## WHAT'S IN THE FULL PACKAGE

<!-- List every file in the evidence directory with a one-line description. -->

```
{{FILE_1}}           ({{FILE_1_DESCRIPTION}})
{{FILE_2}}           ({{FILE_2_DESCRIPTION}})
{{FILE_3}}           ({{FILE_3_DESCRIPTION}})
{{FILE_4}}           ({{FILE_4_DESCRIPTION}})
{{FILE_5}}           ({{FILE_5_DESCRIPTION}})
```

<!-- Flag any files that are operational / not for publication. -->

---

## CONTACT

<!-- How to reach the investigator or primary source for follow-up. -->

**Investigator**: {{INVESTIGATOR_NAME}}
**Preferred contact**: {{INVESTIGATOR_CONTACT_METHOD}}

**Primary source** (available for corroboration): {{SOURCE_NAME}}
**Can corroborate**:
- {{CORROBORATION_1}}
- {{CORROBORATION_2}}
- {{CORROBORATION_3}}

To reach the source: {{SOURCE_CONTACT_INSTRUCTIONS}}
