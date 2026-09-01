# Delta for Capa Offline

## ADDED Requirements

### Requirement: Live Connection Chip in Shared Screen Bar

`.barra-pantalla` (the shared screen header rendered on every in-app screen
that uses it) MUST include a connection-state chip reflecting
`navigator.onLine`. The chip MUST be set synchronously on page load, before
any `online`/`offline` event fires, using the current `navigator.onLine`
value at load time. `window` MUST have `online` and `offline` event
listeners attached that update the same chip's text/weight live, without a
page reload. The chip MUST use the existing `.chip`/`.chip--borde` visual
language (no new visual language introduced). The chip MUST NOT include an
`aria-live` announcement on state change. The chip MUST NOT appear on the
login screen, since `.barra-pantalla` is not rendered there.

This requirement is purely a visibility extension of the existing offline
strategy; it MUST NOT alter draft persistence, the draft restore prompt,
sync-queue behavior, or service-worker caching scope defined elsewhere in
this spec.

#### Scenario: Initial load reflects current connection state without waiting for an event

- GIVEN a user loads an in-app screen that renders `.barra-pantalla`
- WHEN the page finishes loading and `navigator.onLine` is `true`
- THEN the chip shows the "en línea" state immediately, without waiting for an `online` event
- AND when `navigator.onLine` is `false` at load, the chip shows the "offline" state immediately, without waiting for an `offline` event

#### Scenario: Chip updates live when the browser goes offline

- GIVEN a user is on an in-app screen with `.barra-pantalla` visible and the chip shows "en línea"
- WHEN the browser fires an `offline` event on `window`
- THEN the chip updates to the "offline" state without a page reload

#### Scenario: Chip updates live when the browser comes back online

- GIVEN a user is on an in-app screen with `.barra-pantalla` visible and the chip shows "offline"
- WHEN the browser fires an `online` event on `window`
- THEN the chip updates to the "en línea" state without a page reload

#### Scenario: Chip does not appear on the login screen

- GIVEN a user is on the login screen, which does not render `.barra-pantalla`
- WHEN the page loads
- THEN no connection chip is shown

#### Scenario: Chip is independent from the paso-offline draft banner

- GIVEN a wizard step page renders both `.barra-pantalla`'s connection chip and `paso-offline.js`'s draft-restore banner
- WHEN the network state changes
- THEN the connection chip updates independently of the draft-restore banner
- AND `paso-offline.js`'s existing one-shot `navigator.onLine` submit-time check and draft-restore banner logic remain unchanged
