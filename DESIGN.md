---
version: alpha
name: "Intent Workbench"
description: "A compact decision room for inspecting rule outcomes and disagreement."
colors:
  ink: "#1E2429"
  muted: "#616E77"
  paper: "#F4F6F7"
  surface: "#FFFFFF"
  line: "#D7DFE3"
  navy: "#123D55"
  trace: "#146D90"
  resolved: "#13766E"
  missing: "#A46516"
  conflict: "#B4433D"
  focus: "#813CBB"
  scroll-track: "#E6EBED"
  scroll-thumb: "#728A95"
  scroll-hover: "#4B6470"
typography:
  display:
    fontFamily: "Georgia, \"Iowan Old Style\", serif"
  sans:
    fontFamily: 'Inter, "Avenir Next", Avenir, system-ui, sans-serif'
  utility:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
rounded:
  DEFAULT: "3px"
  sm: "3px"
spacing:
  page-max: "1160px"
  panel-gap: "18px"
components:
  native-field: { }
  verdict-panel: { }
  rule-trace: { }
---

# Intent Workbench Design System

## Overview

### Creative North Star

This is a decision room, not an access-control console. The signature is a deep-blue verdict panel paired with a plain-language rule trace: agreement, missing facts, conflict, and no match each have a named state. A compact status key previews the evaluator's four possible outcomes. The panel's strong color anchors attention while the rest of the page stays closer to a technical worksheet.

The product is for PMs and engineers discussing synthetic examples before implementation. It must never resemble a production authorization product or claim to decide real access. Locale is English in v0.1, with system font fallbacks. No Japan-market domain is claimed.

### Token ownership and runtime mapping

`intent_workbench/workbench.css` is the canonical runtime token source. Its `:root` variables style the UI and are embedded verbatim by `core.render_html`; generated HTML adds no independent token layer. Update this file and the exact values below together. There is no separate theme package or external font.

## Colors

`--ink #1e2429`, `--muted #616e77`, `--paper #f4f6f7`, and `--surface #fff` form the worksheet. `--navy #123d55` contains the primary prediction. `--teal #13766e` means resolved, `--amber #a46516` means missing, and `--red #b4433d` means conflict. `--focus #813cbb` is reserved for keyboard focus. State names always appear as text.

## Typography

The title uses `Georgia, "Iowan Old Style", serif`; body uses `Inter, "Avenir Next", Avenir, system-ui, sans-serif`; input identifiers and revision metadata use `ui-monospace, SFMono-Regular, Consolas, monospace`. These stacks use locally installed fonts only.

## Layout

The maximum content width is `1160px`. Input fields form a three-column row on wide screens and collapse to two columns, then one. The prediction and rule trace are side-by-side until `760px`, then stack. The result panel keeps enough height for all status types without layout-dependent actions.

## Elevation & Depth

Thin borders distinguish the input panel and rule trace. The navy result panel is the only saturated large surface. Status dots are a small legend, with text labels adjacent.

## Shapes

3px corners and square marks keep controls tool-like. Buttons and fields use visible borders; no shape or color implies a workflow state by itself.

## Components

Labeled native `select` and `input[type=number]` controls provide unset states. Each field owns help and error text through `aria-describedby`; invalid numeric fields set `aria-invalid`. The reset button clears values and returns focus to the first field. The JSON download includes current inputs and prediction with `expected: null` and `review_status: unconfirmed`. The UI never creates a reviewer confirmation. Rule explanations are rendered through `textContent`; there are no native alert dialogs or remote assets.

## Do's and Don'ts

- Do show every rule's match, no-match, or unknown condition.
- Do preserve confirmed expectations independently from predictions.
- Don't imply the synthetic model authorizes a production action.
- Don't hide an unresolved or conflicting result behind a default.
