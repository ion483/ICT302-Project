# Proposed FR-7 scope change (team decision — 14 November 2026)

**Reason for change:** The requested playback of document construction over time cannot be reliably reconstructed from the available DOCX metadata and RSIDs alone. The document-order paragraph player repeated information available through the normal document preview without fulfilling the historical-reconstruction purpose. Following supervisor guidance to prioritise achievable goals, the team chose to remove that player and retain the recorded creation/last-modified date display.

## Revised FR-7 — Document-property timeline

**Requirement:** The system shall display the available recorded creation and last-modified dates extracted from a supported DOCX document, including available creator/last-modifier properties, in a clearly labelled timeline view. When a property is unavailable, the interface shall indicate its absence. The system shall not claim that these dates or RSIDs reconstruct an edit-by-edit history.

**Delivered:** The summary contains a `Document Timeline` view with recorded creation and modification dates, where available. The earlier RSID/player tab and document-order paragraph player have been removed.

**Removed from scope:** Playback of writing sessions or reconstruction of how a document was constructed over time. This portion of the **original** FR-7 is not delivered.

**Approval:** Team-initiated compromise; **not yet confirmed or accepted by the client**. Record the change, its justification, impact, date, and approving authority in the formal R&A change log. Update any linked use cases, acceptance criteria, design diagrams, test plans, and demo scripts to match. Do not retrospectively describe the original FR-7 as completed.

**Acceptance check:** For a DOCX with recorded timestamps, both appear with the correct labels. If one or both timestamps are absent, the user sees only the available event(s) or an appropriate message. RSID statistics and colour-coded text inspection remain available independently of this timeline.
