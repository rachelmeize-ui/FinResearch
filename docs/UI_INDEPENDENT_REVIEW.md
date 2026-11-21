# FinResearch independent finish review

## 1. Disposition

**FIX — one bounded mobile layout issue before shipping.** No rebuild is needed. The redesign is coherent and substantially improves the original structure. This is the first independent pass, based on the captures generated at approximately 19:30 on 2026-11-21. A corrected mobile provenance table should be recaptured and reviewed before changing the disposition to SHIP.

## 2. Capture validity

- Opened and visually inspected all 16 named final PNGs with `view_image`: desktop home, overview, finance, sources, source drawer, review error, report, empty and blocked; mobile home, studies, research, finance, sources, reports and drawer.
- Inspected the eight original desktop/mobile PNGs to assess the change in structure and density. This is a code-led assessment against the user's pinned direction, not a pixel match to a reference.
- PNG headers confirm desktop widths of 1440 and mobile widths of 390. Source drawer and review-error desktop images are 1440×900; mobile drawer is 390×900. Other images are full-page captures: their taller heights are valid and do not imply a wrong viewport. The 901 px empty/blocked captures are consistent with full-page capture.
- Captures show rendered content, real financial values, complete page bottoms and appropriate open-drawer/error states. They are not blank, unresolved loading views, or misleading crops. The mobile source-table defect is visible in a valid capture and is an implementation issue.
- An additional `failure.png` predates the successful set (19:28 versus 19:30). It was also inspected and looks like the finance screen; it is not evidence of a current failing run. Exclude it from a clean handoff gallery or label it as an earlier diagnostic capture.

## 3. Material findings

### P2 — Mobile provenance evidence action collapses into vertical text

**Evidence:** `test-results/ui-redesign/final/390-sources.png`, the “逐字段来源” table. The rightmost source action is compressed into a sliver, wraps almost character by character, and increases each row to roughly 140 px. The current 560 px internal table window displays only about four records. This materially slows the research intern's central task of connecting a financial value to its annual-report evidence.

**Source:** `static/app.js`, `sourcesPage()` (line 41 in this first pass), uses the shared auto-layout table and `.text-button`. In `static/style.css`, `.text-button` permits normal wrapping without a minimum action width. Other columns have unbreakable company/value strings, allowing the evidence action to absorb the compression.

**Exact bounded fix:** give this provenance table its own class and a minimum width of approximately 680 px; give its evidence button a minimum width of approximately 135 px and `white-space: nowrap`. Keep overflow within the existing table region. Add a short visible mobile instruction such as “左右滑动查看完整来源”. Recapture at 390×900, and verify a user can horizontally reveal and activate the complete source button while the page itself remains within the viewport. Confirm desktop layout is preserved. Do not change the underlying financial values or source records.

No additional ship-blocking material finding was established in the inspected evidence. Minor aesthetic preferences are not included as defects.

## 4. Quality and brief assessment

The light canvas, white working surfaces, restrained blue accent, fine borders, compact 5–8 px rounding and strong table alignment fit the pinned professional financial SaaS direction. There are no gradients, decorative icon tiles, inflated KPI cards, or excessive rounded surfaces. Fiscal.ai/Otio are treated as directional references, not copied pixel layouts. The original dark sidebar and separate task/finance/report framing have become a calmer three-item main navigation and four tabs that preserve task context.

Synthetic role walkthroughs, not user interviews:

- **Newcomer:** company inputs, the research question and one primary “开始研究” action are immediately visible. Supported companies and 2023–2024 coverage are stated beside the action. Empty and blocked states name the missing input and provide import/recovery paths.
- **Securities-research intern:** the shared company title, reporting period, source count and AI review count preserve context. Dotted-underlined figures and explicit “查看依据与核验” controls connect results to the drawer. The mobile provenance table finding is the remaining material obstacle.
- **Financial analyst:** distinct chart/table controls, metric and company selectors, units, separate annual bars, and exact values in tables support comparison. Missing 2023 growth is shown as a dash instead of fabricated data. Net profit scope, minority interests, formula limits and AI draft status are visible. The phone chart uses readable labels and fills its available width. The report is a recognizable document preview with clear exports and draft warnings.

Manual craft-floor assessment was used because the design detector engine is not installed. The pinned brief governs the restrained typography, radii and motion choices. The visible hierarchy, spacing, tabular numerals, focus ring example, selected states, empty state and recovery error are coherent; the source defines hover, disabled, loading, focus-visible and reduced-motion handling. Palette values for main/muted text are sufficiently dark on the supplied neutral surfaces by inspection, but this review is not a computed contrast or full accessibility certification. The side drawer supports the requested evidence-checking task and preserves the financial context behind it.

## 5. Verification limits

- Read the current `static/index.html`, `static/app.js` and `static/style.css`. This reviewer made no application code changes, browser visits, network calls, paid model calls, or production-data mutations.
- `test-results/ui-redesign/final/results.json` reports 12/12 actual Playwright scenarios passing with no errors, isolated copied SQLite data, real annual-report snapshots and zero new paid model calls. `test-results/final.json` reports 57 backend tests, zero failures/errors/skips. These are recorded test results reviewed here, not independently rerun by this reviewer.
- Those results support the recorded cached-document flows, task continuity, validation, review persistence and downloads. They do not establish a fresh external annual-report refetch or successful new AI generation. Existing cached real AI output must remain described accurately as such.
- The screenshot review establishes layout at the named desktop/mobile sizes and states. It does not independently prove every control, all intermediate widths, screen-reader behavior, every keyboard path, or downloaded workbook recalculation/content fidelity.
- Scope remains the historical 2023–2024 public-report research tool; the interface appropriately avoids implying live quotes, valuation, price forecasts or investment recommendations.

### Follow-up: P2 fix verification — 2026-11-21

**Current disposition: SHIP for the reviewed UI redesign scope. P2 score: RESOLVED.** The initial FIX verdict above is retained as the before/after record. This follow-up is limited to the reported mobile provenance-table issue and its desktop regression check; it does not introduce a new broader audit or certify live external services.

Opened the updated `390-sources.png`, the new `390-sources-right.png`, and the updated `1440-sources.png` with `view_image`. All three are valid rendered captures. The initial mobile table now has compact single-line rows and a visible instruction to scroll for raw values/source actions. The horizontally scrolled mobile capture shows complete, single-line “PDF第63页 · 查看来源” actions and the original raw-value column. The source action is no longer compressed into vertical text, and the page remains visually confined to 390 px. The desktop source table retains a clear four-column layout.

Read the scoped implementation: `.provenance-table table` has a 720 px minimum width, the final cell has a 156 px minimum width, and its action uses `white-space: nowrap`. The existing inner scroll region contains the overflow. This directly addresses the observed cause without changing source records or financial values. The coordinating agent reports the browser assertion for the first mobile provenance button is below 48 px high and page overflow remains absent; the updated recorded browser suite is again 12/12 passing with no errors and zero new paid model calls. I inspected the updated result file but did not independently execute those assertions.

Also opened `1440-print-preview.png` for capture validity. It is a valid, populated full-page printable HTML report with coherent neutral/blue typography and visible conclusions, draft statuses and source references. Its financial table is represented as basic pipe-delimited text. Print-table formatting and physical-page pagination are not optimized or independently verified; this should be disclosed as a remaining output-format limitation rather than represented as a polished paginated report. This limitation does not reopen the resolved P2 UI layout finding.

The first-pass verification limits remain in force: cached real reports and existing real AI output are the evidence used; fresh external refetch, new model generation, full accessibility and physical print pagination are not established by this finish review.
