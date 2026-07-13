# Lighthouse and internal-link verification

Verified locally on 2026-07-13 against the built Docker API and web images.

Lighthouse scores for `http://localhost:3000`:

| Category | Score |
|---|---:|
| Performance | 97 |
| Accessibility | 100 |
| Best practices | 100 |
| SEO | 100 |

The Playwright M9 suite also enumerates every rendered same-origin link on the dashboard and incident page and requires each target to return an HTTP status below 400. The browser suite separately checks zero console errors, axe accessibility, keyboard flow, and containment at 375, 768, 1440, and 1920 pixel widths.

Lighthouse was invoked as a disposable CLI against local containers; no analytics payload, credentials, or live provider data was included. Exact fetch time: `2026-07-13T16:05:33.167Z`.
