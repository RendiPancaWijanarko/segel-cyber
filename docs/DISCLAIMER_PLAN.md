# SEGEL Competition Prototype Disclaimer Plan

## 1. Mandate & Scope

This document specifies the implementation plan for the visible disclaimer required across the SEGEL web interfaces.

> **Disclaimer Text**:  
> `"Competition prototype for Kartika Cyber Hackathon 2026, not an official product"`

**Constraint**: This plan is documentation-only; template files must not be altered during the current hygiene phase.

---

## 2. Visual & Placement Specification

### Placement
- **Global Footer**: A persistent, subtle footer positioned at the bottom of the main layout, below active cards and tables.
- **Visual Styling**:
  - Background: Semi-transparent glassmorphic or muted sand tint (`rgba(255, 255, 255, 0.65)` / `var(--segel-sand-subtle)`).
  - Border: 1px solid `var(--segel-sand-border)` (`#E8DFD0`).
  - Font: System sans-serif, size `12px`, weight `500`, color `var(--segel-slate-muted)` (`#64748B`).
  - Badge / Pill: An inline informational badge (e.g., `PROTOTYPE` or `KARTIKA CYBER HACKATHON 2026`) with accent amber/gold border.
  - Non-Intrusive: Positioned without obstructing navigation, interactive scrubbers, or modal dialogs.

---

## 3. Inventory of Template Files Requiring the Disclaimer

The following Jinja2 templates in `src/release_desk/templates/` will receive the disclaimer upon implementation:

1. **`src/release_desk/templates/base.html`**
   - **Role**: Base layout inherited by all primary operational views.
   - **Impact**: Automatically renders the disclaimer footer on:
     - Main Operational Dashboard (`/` via `index.html`)
     - Release Detail & Attestation Trace (`/release/{release_id}` via `release_detail.html`)
     - New Release Authoring Desk (`/release/new` via `new_release.html`)
     - Transparency Ledger Audit Log (`/ledger` via `ledger.html`)
     - Trust Root & Policy Status (`/trust` via `trust.html`)

2. **`src/release_desk/templates/segel.html`**
   - **Role**: Standalone template for the `/zassk` UI/UX R&D environment.
   - **Impact**: Provides dedicated footer placement within the experimental research canvas.

3. **`src/release_desk/templates/error.html`**
   - **Role**: Fallback HTTP error and exception view.
   - **Impact**: Preserves disclaimer visibility during application fault states.

---

## 4. Implementation Snippet (Ready for Future Template Phase)

```html
<footer class="segel-disclaimer-footer" style="margin-top: 32px; padding: 16px 24px; text-align: center; font-size: 12px; color: #64748B; border-top: 1px solid rgba(232, 223, 208, 0.6);">
    <div style="display: inline-flex; align-items: center; gap: 8px;">
        <span style="display: inline-block; padding: 2px 8px; border-radius: 9999px; background: #FEF3C7; color: #92400E; font-size: 11px; font-weight: 700; letter-spacing: 0.05em;">HACKATHON 2026</span>
        <span>Competition prototype for Kartika Cyber Hackathon 2026, not an official product.</span>
    </div>
</footer>
```
