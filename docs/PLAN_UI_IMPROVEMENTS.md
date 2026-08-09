# DocuMind AI — UI Improvement Audit & Phased Plan

Status: **Approved** (Phase 1 shipped; Phases 2-5 pending).
Scope: frontend only (React 19 + Vite + Tailwind v4). Backend and the SSE contract
(`docs/FRONTEND_API_CONTRACT.md`) are **out of scope and must not change**.
Method: component-by-component read of every file under `frontend/src/`, the theme
file (`index.css`), config (`vite.config.js`, `package.json`, `index.html`), and the
API layer. Findings are anchored to `file:line`.

**Theme direction — CONFIRMED DECISION (do not re-litigate):** the app adopts a
**full dark theme app-wide** (Phase 2). Rationale: the auth screen already exists
dark, dark is the conventional aesthetic for a developer/analysis tool, and the
existing token vocabulary (`background`/`surface`/`text`/`text-muted`/`border`) maps
cleanly onto dark surfaces. No light/dark toggle is in scope.

---

## 1. Current-state inventory

| Screen / state | Exists today | Intentional or accidental |
|---|---|---|
| Auth loading screen | plain dark-slate fullscreen, no spinner/logo (App.jsx:60-66) | Accidental |
| Auth modal | hand-rolled inline dark card, toggle, error alert (AuthModal.jsx:98-208) | Feature-driven; outside the design system |
| App shell | fixed `w-80` sidebar (Chats/Docs tabs) + chat canvas drawer-style layout (Layout.jsx:24-92) | Feature-driven; no responsive design |
| Empty chat | robot emoji + 2 suggestion cards (MessageList.jsx:29-50) | Accidental — suggestion cards were inert `<div>`s until Phase 1 |
| History loading | spinner + "Loading conversation history..." (MessageList.jsx:20-27) | Intentional |
| Streaming | "Searching knowledge base..." dots + typewriter token appends + citations from `metadata` (useChatStream.js:135-151, MessageBubble.jsx) | Intentional |
| Citation viewer | modal with filename/page/relevance/excerpt/"View in document" (CitationViewer.jsx) | Intentional |
| PDF viewer | lazy-loaded chunk, page nav, error+retry (PdfViewer.jsx:12-38) | Intentional; most finished component |
| Guardrail refusal / disclaimer | arrives as ordinary SSE `token` frames → renders as a normal assistant bubble | By design; frontend untouched (contract) |
| Error banner | thin red strip above messages, no dismiss (ChatContainer.jsx:43-47) | Accidental-adjacent; dismiss added in Phase 1 |
| Upload dropzone | idle/uploading/polling/error, 3-min poll cap, optimistic delete rollback (UploadPanel.jsx) | Intentional; solid |
| Delete flows | native `window.confirm()` + hover-reveal trash buttons | Accidental; invisible on touch — deferred to Phase 3 |
| Auth expiry | `auth-expired` event → AuthModal (App.jsx:45) | Intentional |
| 429 rate-limit | backend `detail` text already mapped into banner | By design |

---

## 2. Findings (evidence-backed)

### 2.1 Visual design & cohesion

- **F1 — Dead classes (things that "should work" silently do nothing).**
  - `hover:bg-primary-hover` is used across the primary CTA set — Send
    (ChatInput.jsx:36), "View in document" (CitationViewer.jsx:52), "+ New Chat"
    (ConversationSidebar.jsx:28), visibility of the placeholder tests
    — but **`--color-primary-hover` is absent from `@theme`** (index.css:3-11).
    Tailwind v4 only emits utilities for declared theme keys, so **no hover
    feedback exists** anywhere that class is used.
  - `animate-in fade-in zoom-in-95` decorates every modal overlay
    (ChatContainer.jsx:78, CitationViewer.jsx:5-6, PdfViewer.jsx:14) but the
    `tw-animate-css` package that defines those utilities is **not a dependency**
    — all modal open/close transitions are dead CSS.
- **F2 — Two visual languages.** AuthModal carries a full inline dark-slate `styles`
  object (AuthModal.jsx:98-208); the app is light Tailwind. Resolved as: **full dark
  (locked decision above)**.
- **F3 — Brand artifacts.**
  - `<title>frontend</title>` (index.html:7) — the browser tab names the product
    "frontend".
  - Chat header renders "New Session / Persisted Thread" (ChatContainer.jsx:36-38) —
    backend/dev jargon in product UI.
  - Ad-hoc iconography: 🤖 robot (MessageList.jsx), ✨ "logo" (AuthModal), emoji tab
    labels. Phase 1 standardizes the brand mark; full emoji-language cleanup is
    Phase 2.
- **F4 — Affordance lies.** Empty-state suggestion cards look clickable but were inert
  `<div>`s (MessageList.jsx:40-47) — clicking produced nothing.

### 2.2 Responsive / mobile

- **F5 — Unusable below ~800px.** `Layout.jsx` is `flex w-screen` with a fixed `w-80`
  sidebar and `overflow-hidden`; the only `md:` usage is message padding and the
  empty-state grid (MessageList.jsx:40). The chat canvas on a 375px phone is
  unusable. → Phase 3 (drawer + overlay).
- **F6 — Touch-channel dead actions.** Deletes are `opacity-0 group-hover:opacity-100`
  (ConversationItem.jsx:12, DocumentSidebar.jsx:51) — invisible on touch. → Phase 3.

### 2.3 Accessibility

- **F7 — Modals break keyboard flows.** CitationViewer + PdfViewer overlays have no
  focus trap, no Escape-to-close, no `role="dialog"`/`aria-modal`, no return-focus;
  `✕` buttons lack `aria-label`. Exactly **one** `aria-label` exists in the app (the
  doc-delete button). → Phase 4 (shared dialog primitive).
- **F8 — Streaming invisible to screen readers.** Tokens append into message content
  with no `aria-live`; no completion cue. → Phase 4.
- **F9 — Form labeling.** ChatInput textarea has placeholder-only labeling
  (ChatInput.jsx:15); auth inputs lack `htmlFor`/id and `autocomplete`. → Phase 4.
- **F10 — Native `window.confirm()`** for deletes (ConversationItem.jsx:22,
  DocumentSidebar.jsx:30) before JS-dialog. → Phase 3 (inline confirm, same
  chance).
  -  **Phase 1 note:** kept `window.confirm` intact — an in-app confirm belongs with
    the shared dialog primitive (Phase 3/4), shipping it half-finished ahead of that
    would violate a meet-quality bar for an a11y-relevant control.

### 2.4 Micro-interactions / perceived performance

- **F11 — Streaming idle cue.** "Searching knowledge base..." dots persist even after
  the first token lands (MessageList.jsx:34) — collapse them at first token. → Phase 5.
- **F12 — Detail polish.** UploadPanel says "( .pdf, .md)" while `accept` includes
  `.txt` (UploadPanel.jsx:15,108-111); banner has no dismiss; PDF modal uses pdf.js's
  default loading text with no "Loading document…" state. → Phase 1 fixes the hint
  and banner; PDF loading state is Phase 5.
- **F13 — Dead code (zero importers, verified by grep).**
  - `fetchDocumentFileResponse` (services/api.js:254) — PdfViewer uses
    `buildDocumentFileRequest` instead.
  - `sendChatMessage` (services/api.js:271) and `sendChatMessageStream`
    (services/api.js:295) — superseded by the client-side SSE loop in
    `useChatStream.js`.
  - `src/lib/api.js` — single-line re-export shim consumed only by UploadPanel
    (UploadPanel.jsx:2).
  - Removed in Phase 1; UploadPanel re-pointed at `services/api`.

### 2.5 Backend-contract boundary (report only)

- Guardrail refusal/disclaimer arrive through the existing SSE event sequence
  (`metadata` → `token` → `done`) and render as a normal assistant message — **no
  frontend or contract change** is required for them to look intentional.
- 429s / stream timeouts already funnel into the banner via `detail` +
  `friendlyNetworkMessage`. Nothing in this plan touches
  `docs/FRONTEND_API_CONTRACT.md`, the chat routes, or the eval/guardrail work.

---

## 3. Prioritization

| Priority | Findings | Why |
|---|---|---|
| High / Low-effort | F1 (tokens+animations), F3 (brand), F4 (cards), F13 (dead code), banner dismiss, F12 copy | Visible on first open; ~1 file each; Phase 1 |
| High / High-effort | F2 (dark theme, locked), F5 (mobile), F6 (touch deletes) | The coherence story; multi-file; Phases 2-3 |
| Medium | F7 (dialog skeleton), F10 (inline confirm) | Phase 4 / bundled |
| Backlog | F8 (live region), F9 (labels), F11 (stream cue), PDF loading, skeletons | Meaningful but not tour-visible; Phases 4-5 |

---

## 4. Phased plan (each phase independently shippable + reviewable)

| Phase | Scope | Effort | Status |
|---|---|---|---|
| 1 | Tokens/animations live; brand (title/meta/jargon); suggestion cards clickable; F13 dead-code removal; banner dismiss; upload-hint copy | S | **SHIPPED** |
| 2 | Full dark theme: single token family, component migration, AuthModal onto the system, one icon language | M | Pending |
| 3 | Mobile drawer + touch-visible deletes + in-app delete confirm | M | Pending |
| 4 | Shared dialog primitive (focus trap, Escape, aria-modal), labels, live region for streaming | M | Pending |
| 5 | Streaming idle cue, PDF "Loading document…" state, docs-list skeletons | S | Pending |

Acceptance per phase: `npm run lint`, `npm test`, `npm run build` stay green; no
backend/contract changes.

---

## 5. Decisions

- **D1 — Full dark theme, app-wide, no toggle (locked).** Phase 2.
- **D2 — No new UI dependencies.** No animation library, no modal/drawer library —
  dialogs hand-rolled on Tailwind v4. The one exception is **tw-animate-css**
  (already added in Phase 1) because the audit's dead `animate-in` classes literally
  reference its utilities; adding the library that owns the vocabulary is cheaper and
  more honest than re-skinning every modal by hand.
- **D3 — `window.confirm` stays until Phase 3.** Replacing it needs the shared dialog
  primitive (Phase 4 building block); shipping a half-done confirm ahead of that
  trades UX debt now. Noted here so nobody reopens it as a "miss".
- **D4 — Backend immutable.** The refusal/disclaimer "looks like a normal bubbles" is
  correct and complete behavior; never special-case it on the wire.