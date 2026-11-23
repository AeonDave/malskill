# Browser evidence viewers

Load when implementing or reviewing a skill-app's browser viewer or dashboard. Keep persisted state, service ownership and finalization in [runtime](runtime.md); this reference covers the interface over that state.

## Establish the browser contract

- Use the project's actual browser versions, embedded WebView and delivery mode: served page, local file, offline export, or host panel. A browser engine name alone does not establish API support or permission availability.
- Consult current feature support, then detect the exact optional API or CSS feature. [Baseline browser mappings](https://web-platform-dx.github.io/supported-browsers) have WebView exceptions; availability is not proof of accessibility or correct application behavior.
- Preserve reading, navigation and required actions without optional enhancements. Reuse the existing component library when it meets the contract; native support is not a reason to replace working controls or add unrequested features.
- Bundle required offline resources. If an enhancement or its dependency cannot load, retain the core interface or report the specific unavailable capability. A syntax/API check alone does not exercise the fallback.

## Choose controls by behavior

| Need | Implementation and verification |
|---|---|
| Modal action or detail view | Use a supported `<dialog>` opened with `showModal()`, or an existing accessible modal. Give it an accessible name and visible close action; verify initial focus, keyboard containment, dismissal and return focus. Merely setting `open` does not create a modal. |
| Nonmodal supplementary content | A popover may handle top-layer display and dismissal. It does not make the background inert or automatically provide menu/dialog semantics; keep triggers and keyboard behavior appropriate to the content. |
| Filters, search and submission | Prefer labeled native inputs and form submission. If adding custom Enter shortcuts, preserve IME composition and newline behavior; test the target input methods. Keep an explicit submit action. |
| Validation and progress | Associate visible errors with the relevant inputs and update accessible state when errors are exposed. Announce meaningful progress/status changes without flooding live regions; retain partial, failed and unknown states. |
| Dense evidence table | Preserve table headings and cell relationships. For narrow layouts, use an appropriately named, keyboard-scrollable overflow region; verify focus visibility. Do not substitute CSS-generated labels for the only accessible headers. |

Check keyboard-only use, focus after filtering/removing rows, zoom/reflow, reduced-motion behavior when animation exists, and the intended assistive technology. Native controls reduce custom behavior but still need application-level checks. See [dialog and popover behavior](https://web.dev/articles/baseline-in-action-dialog-popover) and [WAI form notifications](https://www.w3.org/WAI/tutorials/forms/notifications/).

## Improve the measured slow path

Reproduce a slow import, filter, navigation or render with representative artifact sizes. Distinguish JavaScript processing, DOM/layout, paint and resource loading before changing code. Compare the same workload and preserve correctness, cancellation and evidence ordering; an API change alone is not a speedup.

- **Long processing loops:** split work into bounded chunks and check cancellation between them. Feature-detect `scheduler.yield()`; an awaited `setTimeout` can yield where unavailable, but lacks its prioritized continuation. `await Promise.resolve()` only queues a microtask and is not a rendering/input yield. Yielding between items cannot interrupt one expensive synchronous operation; move appropriate CPU work to a worker or change the algorithm. Choose chunk size from measurements, not a universal time budget. See [long-task guidance](https://web.dev/articles/optimize-long-tasks).
- **Heavy offscreen sections:** consider `content-visibility: auto` when layout/paint is the bottleneck. Reserve suitable dimensions or an intrinsic-size estimate to avoid scroll jumps. It does not eliminate parsing, data storage or the DOM, and is not virtualization. Normal rendering is a valid unsupported-browser fallback. Verify keyboard navigation, find-in-page, anchors and print/export; keep canonical data available independently of deferred rendering. See [content visibility](https://web.dev/articles/content-visibility).
- **Images:** for already-authorized image resources, avoid lazy-loading the initially visible primary evidence image; lazy-load offscreen thumbnails where useful and reserve dimensions. Apply `fetchpriority="high"` only when measurement supports prioritizing a critical image; it is a hint, not a load guarantee. See [LCP optimization](https://web.dev/articles/optimize-lcp).

Before adding resource hints, remote thumbnails or prefetch/prerender rules, apply the outbound-loading boundary in [browser-output](../../../coding-behaviours/secure-tooling-implementation/references/browser-output.md). Performance work must not silently contact evidence URLs or change the meaning of user actions.

## Verify the delivered interface

Select checks for the implemented behavior:

- Required actions with optional APIs unavailable, including dependency-load failure.
- Keyboard, focus, error announcement, narrow layout and zoom on the supported host.
- Representative large input, repeated filtering, cancellation and stale-result suppression.
- Correct visible values and ordering against persisted evidence; rendering optimizations must not omit records from exports or searches that promise full coverage.
- Final export reopened from its delivered location, with network disabled when offline operation is promised.

Report actual browser/build and tested paths. Static HTML inspection, a mock DOM, an accessibility scan or an HTTP success response cannot alone establish interactive correctness or cross-browser support.
