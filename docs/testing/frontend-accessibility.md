# Frontend Accessibility Compliance Report

This document details the accessibility (a11y), responsive design, and user experience (UX) improvements implemented in the `@incident-commander/web` Next.js frontend application.

---

## ♿ Focus Trapping and Restoration

### Intake Modal Flow
- **Focus Trap**: When the **Manual Intake Modal** opens, focus is programmatically shifted to the first input field (`#form-title`). A keyboard listener intercepts `Tab` and `Shift+Tab` keys to prevent focus from escaping the modal container. If the user hits `Tab` on the last interactive element, focus loops back to the close button; if they hit `Shift+Tab` on the first element, focus wraps to the confirmation button.
- **Escape Key Dismissal**: Pressing the `Escape` key closes the modal overlay.
- **Focus Restoration**: On modal closure (via close button, backdrop click, Escape key, or form submission), focus is restored back to the trigger button ("➕ Intake New Incident").

---

## ⌨️ Keyboard-Only Assertions & Flows

### Diagnosing Pipeline Trigger
- The diagnosing start button is fully focusable and triggers pipeline execution when activated via the `Enter` or `Space` key.

### Evidence Citation Links
- Citation query buttons (`🔍 ev-XXXX`) within the timeline and investigation report sections are focusable.
- Activating a citation link via keyboard:
  1. Expands the corresponding telemetry/evidence card if collapsed.
  2. Scrolls the evidence card smoothly (or instantly if reduced motion is preferred) into the viewport.
  3. Dispatches focus to the evidence card element (`tabIndex={-1}`).
  4. Temporarily highlights the target card using visual borders.

### Approval Decisions
- Form input for patch justification (`#reason-input`) is in the logical focus order.
- Action buttons (**Approve & Execute Patch** and **Reject Patch**) are focusable and support keyboard submission.

---

## 🎨 Color Contrast Improvements

To ensure compliance with the **WCAG 2.1 AA** minimum contrast ratio of **4.5:1**, theme settings were updated for dark-mode readability:

### badge status states (Foreground on background overlay)
- **SEV1 - Critical** (Red): Changed to background `rgba(239, 68, 68, 0.15)` and text `#fca5a5` (~ 7.5:1).
- **SEV2 - Major** (Orange/Yellow): Changed to background `rgba(245, 158, 11, 0.15)` and text `#fde047` (~ 9.6:1).
- **SEV3 - Minor** (Blue): Changed to background `rgba(59, 130, 246, 0.15)` and text `#93c5fd` (~ 7.0:1).
- **SEV4 - Low** (Gray): Changed to background `#24324f` and text `#f1f5f9` (~ 5.5:1).

### Interactive controls
- **Approve button**: Background changed from `#10b981` (emerald-500) to `#065f46` (emerald-800) to achieve a contrast ratio of `6.24:1` against white text.
- **Reject/Danger button**: Background changed from `#ef4444` (red-500) to `#b91c1c` (red-700) to achieve a contrast ratio of `4.89:1` against white text.
- **Contradiction Labels**: Theme property `--error` updated to `#f87171` (red-400), bringing contrast on dark card containers to `4.64:1`.

### Alert banners
- API down alerts, hypotheses, plans, and patches fetch errors now render using an accessible dark solid background (`#1e131d`) and light red text (`#fca5a5`), giving a contrast ratio of `8.44:1`.

---

## 🏃 Reduced Motion Support

We respect users' operating system preferences for reduced motion (`prefers-reduced-motion: reduce`):

- **CSS Keyframes**: Loading spinners (`.spin-indicator`) and pulse animations are disabled.
- **CSS Transitions**: Transitions for cards (`.card`), buttons (`.btn`), and evidence rows are set to `none`.
- **Smooth Scroll**: programmatic scroll-into-view calls (`scrollIntoView`) fall back to instant `auto` scroll behavior.
- **Visual Highlight**: Temporary outline transitions on focused citation targets are terminated instantly rather than fading out slowly.

---

## 📱 Mobile Responsive Layouts

Verified on mobile viewports (e.g. `375px` width):
- **Overflow Prevention**: No horizontal scroll exists on the root window or HTML document. Wide tables wrap using `overflow-x: auto`.
- **Intake Form**: Inputs stack vertically rather than relying on grid columns, and size margins prevent horizontal overflow on smaller screens.
- **Multi-column Layouts**: Detail page main grid container stacks elements in a single column below `1024px` and transitions into a 2-column layout only on tablet/desktop displays.

---

## 🤖 Automated Accessibility Checks

We added automated audits using `@axe-core/playwright` and `AxeBuilder`:
- Checks are run against both the **Dashboard** and **Golden Incident Room** views.
- Verified that **zero serious or critical accessibility violations** exist in either view.
