# 2026-11-14 — Secondary numbered RSID indicator display fix

## Symptom
The small numbered labels for text-run RSID groups disappeared in the document preview after the timeline/player was removed.

## Cause
The player-removal edit left an orphan CSS declaration (`color: #21384e; }`) immediately before `.document-content .rsid-run[data-rsid-number]::before`. A CSS parser treated the declaration and the following selector as one malformed rule, preventing the number-label pseudo-element from rendering.

## Resolution
Deleted only the orphan CSS declaration, restoring the valid `::before { content: attr(data-rsid-number); ... }` rule. The original `enableParagraphSelection()` RSID numbering logic, RSID colours, analysis data, and Created/Modified timeline remain unchanged. The removed timeline/player is **not** restored.

## Verification
- 21 automated tests pass (including a regression test guarding this CSS/JS integration).
- CSS parsed to verify the `::before` rule is recognized and its `content` equals `attr(data-rsid-number)`.
- Windows packaged EXE not rebuilt or tested in this environment; rebuild with PyInstaller and confirm using a Word-authored DOCX that contains usable run RSIDs.
