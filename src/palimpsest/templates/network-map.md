# NETWORK MAP — {{INVESTIGATION_NAME}}

<!--
  INSTRUCTIONS FOR THE JOURNALIST

  This is a standalone network / relationship map. It shows who knows whom,
  who worked where, who reports to whom, and how everything connects.
  Use it alongside the dossier to trace influence, opportunity, and motive.

  Fill in every {{PLACEHOLDER}}. Add nodes and edges to the Mermaid graph
  as needed.
-->

**Compiled**: {{DATE_COMPILED}}
**Investigator**: {{INVESTIGATOR_NAME}}
**Part of dossier**: {{DOSSIER_FILENAME}}

---

## What This Map Shows

{{NETWORK_INTRO_PARAGRAPH}}

<!--
  2-4 sentences. What is this map trying to illustrate? A talent-farming
  network? A set of institutional overlaps? A conspiracy of opportunity?
  Be honest about what the map proves and what it merely suggests.
-->

---

## Mermaid Graph

<!--
  Paste the Mermaid graph here. The graph uses standard Mermaid graph TD
  (top-down) syntax. Each entity is a node; relationships are edges.

  Node naming convention: use short, unique IDs (e.g., AC for Alice Chen,
  JS for Jane Smith). Add a label in square brackets.

  Edge colouring and styling are done in the graph itself — see the Legend
  section below for conventions to follow.

  Tip: if the graph gets large, split into subgraphs for clarity.
-->

```mermaid
graph TD
    %% ——— ENTITY NODES ———

    {{ENTITY_1_ID}}["{{ENTITY_1_LABEL}}"]
    {{ENTITY_2_ID}}["{{ENTITY_2_LABEL}}"]
    {{ENTITY_3_ID}}["{{ENTITY_3_LABEL}}"]
    {{ENTITY_4_ID}}["{{ENTITY_4_LABEL}}"]
    {{ENTITY_5_ID}}["{{ENTITY_5_LABEL}}"]
    {{ENTITY_6_ID}}["{{ENTITY_6_LABEL}}"]
    {{ENTITY_7_ID}}["{{ENTITY_7_LABEL}}"]
    {{ENTITY_8_ID}}["{{ENTITY_8_LABEL}}"]

    %% ——— RELATIONSHIP EDGES ———

    {{ENTITY_1_ID}} -->|{{RELATION_LABEL_1}}| {{ENTITY_2_ID}}
    {{ENTITY_2_ID}} -->|{{RELATION_LABEL_2}}| {{ENTITY_3_ID}}
    {{ENTITY_3_ID}} -.->|{{RELATION_LABEL_3}}| {{ENTITY_4_ID}}
    {{ENTITY_4_ID}} ===>|{{RELATION_LABEL_4}}| {{ENTITY_5_ID}}
    {{ENTITY_1_ID}} -->|{{RELATION_LABEL_5}}| {{ENTITY_6_ID}}
    {{ENTITY_6_ID}} -.->|{{RELATION_LABEL_6}}| {{ENTITY_7_ID}}
    {{ENTITY_7_ID}} -->|{{RELATION_LABEL_7}}| {{ENTITY_8_ID}}
    {{ENTITY_8_ID}} -.->|{{RELATION_LABEL_8}}| {{ENTITY_1_ID}}

    %% ——— SUBGRAPHS (OPTIONAL) ———
    %% Uncomment and adapt:

    %% subgraph {{SUBSGRAPH_1_LABEL}}
    %%     {{ENTITY_1_ID}}
    %%     {{ENTITY_2_ID}}
    %% end

    %% subgraph {{SUBSGRAPH_2_LABEL}}
    %%     {{ENTITY_3_ID}}
    %%     {{ENTITY_4_ID}}
    %% end
```

<!--
  Quick Mermaid reference:
    Node:   ID["Display Name"]
    Edge:   ID1 --> ID2                    directional link
            ID1 --- ID2                    bidirectional/neutral link
            ID1 -.-> ID2                   dashed directional (inferred)
            ID1 ===> ID2                   thick directional (institutional)
            ID1 -.->|"label text"| ID2     dashed with label
-->

---

## Legend

### Line Types

| Line | Meaning |
|---|---|
| `A --- B` | Confirmed direct relationship (worked together, known to each other) |
| `A --> B` | Directional relationship (A reports to B, A influenced B, A hired B) |
| `A -.-> B` | Inferred / plausible relationship (circumstantial, not confirmed) |
| `A ===> B` | Institutional affiliation (both in same organisation, lodge, board) |
| `A -..- B` | Indirect link via intermediary (A knows B through C) |

### Colours

<!--
  Assign confidence colours consistently. If the Mermaid renderer you're using
  supports CSS classes, define them in a style block. Otherwise, annotate
  nodes with colour suffixes in the label.
-->

| Colour | Confidence | Meaning |
|---|---|---|
| Green `#00FF00` | **High** | Verified through multiple independent sources |
| Amber `#FFA500` | **Medium** | Plausible but missing corroboration |
| Red `#FF4444` | **Low** | Speculative — included to track a lead |
| Grey `#888888` | **Unknown** | Node exists but relationship confidence not yet assessed |

<!--
  Node styling in Mermaid (if supported):

    style {{ENTITY_ID}} fill:#00FF00,stroke:#333,stroke-width:2px

  Where fill colour maps to the confidence table above.
-->

### Node Shapes

| Shape | Meaning |
|---|---|
| `[Name]` (rectangle) | Individual person |
| `{Name}` (rhombus) | Organisation / company |
| `(Name)` (rounded) | Group / collective / informal network |
| `>Name]` (flag) | Online account / alias / persona |

---

## Entities in This Map

<!--
  Table of every node in the graph. One row per entity. Include a brief
  description and confidence for the entity's role in the investigation.
-->

| ID | Entity | Type | Description | Confidence | Link to dossier |
|---|---|---|---|---|---|
| {{ENTITY_1_ID}} | {{ENTITY_1_NAME}} | {{ENTITY_1_TYPE}} | {{ENTITY_1_DESCRIPTION}} | {{ENTITY_1_CONFIDENCE}} | {{ENTITY_1_DOSSIER_LINK}} |
| {{ENTITY_2_ID}} | {{ENTITY_2_NAME}} | {{ENTITY_2_TYPE}} | {{ENTITY_2_DESCRIPTION}} | {{ENTITY_2_CONFIDENCE}} | {{ENTITY_2_DOSSIER_LINK}} |
| {{ENTITY_3_ID}} | {{ENTITY_3_NAME}} | {{ENTITY_3_TYPE}} | {{ENTITY_3_DESCRIPTION}} | {{ENTITY_3_CONFIDENCE}} | {{ENTITY_3_DOSSIER_LINK}} |
| {{ENTITY_4_ID}} | {{ENTITY_4_NAME}} | {{ENTITY_4_TYPE}} | {{ENTITY_4_DESCRIPTION}} | {{ENTITY_4_CONFIDENCE}} | {{ENTITY_4_DOSSIER_LINK}} |
| {{ENTITY_5_ID}} | {{ENTITY_5_NAME}} | {{ENTITY_5_TYPE}} | {{ENTITY_5_DESCRIPTION}} | {{ENTITY_5_CONFIDENCE}} | {{ENTITY_5_DOSSIER_LINK}} |
| {{ENTITY_6_ID}} | {{ENTITY_6_NAME}} | {{ENTITY_6_TYPE}} | {{ENTITY_6_DESCRIPTION}} | {{ENTITY_6_CONFIDENCE}} | {{ENTITY_6_DOSSIER_LINK}} |
| {{ENTITY_7_ID}} | {{ENTITY_7_NAME}} | {{ENTITY_7_TYPE}} | {{ENTITY_7_DESCRIPTION}} | {{ENTITY_7_CONFIDENCE}} | {{ENTITY_7_DOSSIER_LINK}} |
| {{ENTITY_8_ID}} | {{ENTITY_8_NAME}} | {{ENTITY_8_TYPE}} | {{ENTITY_8_DESCRIPTION}} | {{ENTITY_8_CONFIDENCE}} | {{ENTITY_8_DOSSIER_LINK}} |

<!--
  Entity types: Person, Organisation, Online Account, Informal Group,
  Government Body, Corporate Entity.
-->

---

## Key Relationships (Narrative Summary)

<!--
  Optional section. Describe the most important relationships in prose,
  explaining why they matter to the investigation. This is where you
  connect dots that the graph shows but doesn't explain.
-->

### {{RELATIONSHIP_1_LABEL}}

{{RELATIONSHIP_1_DESCRIPTION}}

**Evidence**: {{RELATIONSHIP_1_EVIDENCE}}

**Confidence**: {{RELATIONSHIP_1_CONFIDENCE}}

---

### {{RELATIONSHIP_2_LABEL}}

{{RELATIONSHIP_2_DESCRIPTION}}

**Evidence**: {{RELATIONSHIP_2_EVIDENCE}}

**Confidence**: {{RELATIONSHIP_2_CONFIDENCE}}

---

### {{RELATIONSHIP_3_LABEL}}

{{RELATIONSHIP_3_DESCRIPTION}}

**Evidence**: {{RELATIONSHIP_3_EVIDENCE}}

**Confidence**: {{RELATIONSHIP_3_CONFIDENCE}}

---

## Gaps

<!--
  What relationships are you missing? What would complete the picture?
-->

- {{GAP_1}}
- {{GAP_2}}
- {{GAP_3}}

---

## Sources for This Map

<!--
  Where did the relationship data come from? Link to the specific evidence
  files or source records.
-->

- {{SOURCE_1}}
- {{SOURCE_2}}
- {{SOURCE_3}}
- {{SOURCE_4}}
