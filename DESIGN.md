---
name: ExcelPoint
description: A calm study app where XP, your AI study assistant, answers only from your own files and shows the passage behind every answer.
colors:
  primary: "#2563eb"
  primary-hover: "#1d4ed8"
  primary-fill: "#2563eb"
  primary-fill-hover: "#1d4ed8"
  primary-soft: "#eff6ff"
  primary-on-dark: "#93c5fd"
  focus: "#2563eb"
  ai-one: "#667eea"
  ai-two: "#764ba2"
  ai-text: "#764ba2"
  ai-soft: "#f3f0ff"
  success: "#06a77f"
  success-text: "#047857"
  success-soft: "#e6fbf5"
  warning: "#d97706"
  warning-text: "#b45309"
  warning-soft: "#fff7e6"
  danger: "#ef4444"
  danger-fill: "#dc2626"
  danger-text: "#b91c1c"
  input-border: "#8492a6"
  danger-soft: "#fef2f2"
  ink: "#1e293b"
  muted: "#5f6e82"
  border: "#e2e8f0"
  background: "#f8fafc"
  card: "#ffffff"
  hover: "#f1f5f9"
  primary-dark: "#60a5fa"
  primary-hover-dark: "#93c5fd"
  focus-dark: "#60a5fa"
  ai-text-dark: "#a5b4fc"
  danger-text-dark: "#f87171"
  input-border-dark: "#64748b"
  success-dark: "#06d6a0"
  warning-dark: "#f59e0b"
  ink-dark: "#f1f5f9"
  muted-dark: "#94a3b8"
  border-dark: "#334155"
  background-dark: "#0f172a"
  card-dark: "#1e293b"
  sidebar-dark: "#172033"
  hover-dark: "#273449"
typography:
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "28px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 650
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  ui:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 500
  meta:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 700
  wordmark:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 800
    letterSpacing: "-0.045em"
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  pill: "20px"
spacing:
  page-top: "36px"
  page-x: "40px"
  page-x-phone: "16px"
  section-gap: "28px"
  card-padding: "16px"
components:
  button-primary:
    backgroundColor: "{colors.primary-fill}"
    textColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.primary-fill-hover}"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.hover}"
  button-danger:
    backgroundColor: "{colors.danger-fill}"
    textColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-ai:
    backgroundColor: "{colors.ai-one}"
    textColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  badge-neutral:
    backgroundColor: "{colors.hover}"
    textColor: "{colors.muted}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  badge-primary:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  badge-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success-text}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  text-input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "42px"
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: "{spacing.card-padding}"
  answer-evidence:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "12px 14px"
---

# Design System: ExcelPoint

## Overview

**Creative North Star: "The Quiet Study Desk"**

ExcelPoint is a clean, quiet workspace that gets out of the way of studying. Cool slate neutrals, white cards on a near-white ground, one brand blue for action and wayfinding, and Inter throughout. Nothing shouts; the loudest thing on a screen is the next useful task. Density is moderate, Linear and Notion-like: lists and cards with thin 1px borders, a soft two-layer shadow, gently rounded 8px corners.

The one place the world changes register is XP. The purple gradient belongs to XP and nowhere else, so a student always knows when the AI study assistant is speaking or working. And every XP answer carries its proof: the passage from the student's own file, matched words marked, sitting directly under the answer. That evidence block is the signature of the whole system. Answers you can check beat answers that sound good, and the interface makes the checking visible.

Motion is calm and fast: short ease-out settles, no bounce, nothing a student has to wait for. Light and dark themes are equal citizens, both held to WCAG AA. The logged-out landing page (`/app/welcome`, the Persuade surface) lives in this same world and may use larger display type (Inter 800 to 850, tight tracking) on the same tokens; the app itself has no display size.

**Key Characteristics:**
- Cool slate neutrals, one brand blue, purple reserved for XP.
- Thin 1px borders plus a faint ambient shadow; flat, not layered.
- Sentence case everywhere; one heading weight (650).
- Text sized by role: 12 label, 13 meta, 14 UI, 16 for anything read.
- The source passage under every XP answer.
- Calm, fast, ease-out motion that switches off for reduced motion.

## Colors

A cool slate palette with a single confident blue and a purple gradient held back for XP.

### Primary
- **Study Blue** (primary / primary-fill): the brand blue. Primary buttons, active navigation, links, citation chips, progress bars, the P in the wordmark. In light theme the text role and the fill role share one value.
- **Pressed Study Blue** (primary-hover / primary-fill-hover): hover for blue fills.
- **Blue Wash** (primary-soft): the active nav pill, selected rows, empty-state and upload icon tiles, the "not in your materials" reply, evidence highlight base.
- **Night Sky Blue** (primary-dark): dark theme's text-and-marks blue. It passes AA on dark cards where the old #3b82f6 did not. Fills in dark theme stay on primary-fill.
- **Pale Blue on Dark** (primary-on-dark): blue text that sits on a dark fill.
- **Focus Blue** (focus / focus-dark): keyboard focus rings only.

### Secondary
- **XP Gradient** (ai-one to ai-two, 135deg): the XP avatar tile, Ask XP and AI action buttons, the send button, AI notification icons, quiz generation progress. Never decoration. Where white text or an icon sits on it (buttons, send), the gradient starts at #5a67d8, because white on #667eea is only 3.7:1.
- **Subject tiles** use teal, blue and green initials tiles; never purple, which belongs to XP.
- **XP Violet Text** (ai-text / ai-text-dark): purple text on the XP wash. ai-one is too light for text.
- **XP Wash** (ai-soft): background for XP-tagged badges and ranks.

### Tertiary
- **Mint** (success, success-text, success-soft; success-dark in dark): verified answers, ready files, high confidence, right answers.
- **Amber** (warning, warning-text, warning-soft; warning-dark in dark): pending states, unverified notes, rate-limit banners, moderate confidence.
- **Signal Red** (danger, danger-fill, danger-text, danger-soft): errors, low confidence, delete. danger-fill carries white text; danger-text (#b91c1c, dark #f87171) is for red text; danger is for borders and marks only, since it is 3.4-3.9:1 as text.

### Neutral
- **Slate Ink** (ink / ink-dark): all primary text.
- **Slate Muted** (muted / muted-dark): secondary lines, captions, timestamps. Darker than the prototype's #64748b so it passes AA on tinted backgrounds too.
- **Hairline** (border / border-dark): every 1px border and divider.
- **Paper** (background / background-dark): the page ground, chat history and sources panels.
- **Card White** (card / card-dark): cards, modals, dropdowns, the composer. In dark theme the sidebar sits a step lower (sidebar-dark).
- **Hover Slate** (hover / hover-dark): hover rows, the user's chat bubble, neutral badge fill, progress tracks.

### Named Rules
**The Fill Versus Text Rule.** White text sits only on primary-fill, danger-fill or the XP gradient. A colour named for text (primary, danger-text, ai-text) is never a background for white text, and in dark theme primary (#60a5fa) is for text and marks only.

**The XP Owns Purple Rule.** The gradient and the purple washes appear only where XP speaks or works: the XP avatar, Ask XP, AI actions, the composer. If a surface is not XP, it is not purple.

## Typography

**Display Font:** none in the app. The landing page may use Inter 800 to 850 with tight tracking.
**Body Font:** Inter (with system-ui, sans-serif)
**Label/Mono Font:** ui-monospace, SFMono-Regular, Menlo, Consolas for code inside answers only.

**Character:** one family, sized by job rather than by hierarchy. Plain and literal for second-language readers on phones.

### Hierarchy
- **Headline** (650, 28px, 1.25, -0.035em; 23px on phones): page titles.
- **Title** (650, 16px, -0.015em): section headings. Modal titles step up to 19px, dialog titles to 18px.
- **Body** (400, 16px, 1.65 in answers, 1.6 in passages): anything a student reads: answers, evidence passages, summaries, card backs.
- **UI** (500 to 600, 14px): buttons, navigation, list items, form labels.
- **Meta** (400 to 700, 13px): timestamps, captions, secondary lines, badges. The floor for visible text.
- **Label** (700, 12px): the unread count and the phone tab bar only.
- **Wordmark** (800, 17px, -0.045em): "Excel**P**oint" with the P in primary.

### Named Rules
**The One Heading Weight Rule.** Every h1 to h4 is weight 650 with `text-wrap: balance`; paragraphs and list items use `text-wrap: pretty`.

**The Read At Sixteen Rule.** Anything a student reads to learn is 16px. Phones also keep every input at 16px so iOS never zooms.

**The Sentence Case Rule.** No all-caps, no tracked-out labels, no kicker or eyebrow line above a heading. A heading stands alone.

## Layout

A fixed left sidebar (240px, collapses to 72px) beside a sticky 64px top bar with a light blur; content sits in a centred column up to 1360px with 36px top and 40px side padding. Home is a two-column grid (main plus a 340px side column, 28px gap); sections stack 28px apart. Chat is full-bleed: a 220px history column, the thread (messages centred to 720px), and a 300px Sources panel that is closed until wanted.

Responsive: under 1100px the Sources panel becomes a slide-over with a scrim; under 900px the sidebar stays at icon width; at 640px and below the sidebar becomes a five-tab bottom bar (68px, safe-area aware), the top bar drops to 56px, page padding drops to 16px, modals become bottom sheets, toasts move to the top, and every touch target is at least 44px. No sideways scrolling at 375px.

## Elevation & Depth

Flat with a whisper of lift. Surfaces are separated by 1px Hairline borders first and a very soft ambient shadow second; depth is never the main separator. Floating layers (modals, dropdowns, toasts, slide-over panels) get the one strong shadow. Dark theme uses the same two steps with darker shadow tints, and relies on the card versus background tone step more than on shadow.

### Shadow Vocabulary
- **Resting** (`box-shadow: var(--shadow)`, light `0 1px 2px rgb(15 23 42 / .04), 0 5px 16px rgb(15 23 42 / .035)`): cards, list cards, the composer.
- **Floating** (`box-shadow: var(--shadow-lg)`, light `0 20px 45px rgb(15 23 42 / .14)`): modals, dropdowns, toasts, slide-over panels.
- **Field ring** (`0 0 0 3px rgb(37 99 235 / .1)`): focused text fields and the focused source excerpt; the composer uses the XP tint `rgb(102 126 234 / .1)`.

### Named Rules
**The Border First Rule.** Separate with a 1px border before reaching for a shadow; a strong shadow means the layer floats above the page.

## Shapes

Gently rounded throughout. The base radius is 8px (rounded.md) for buttons, inputs, cards and the evidence block. Larger containers that frame a whole task (modals, the review hero, the quiz question card, empty states, auth card) use 12px (rounded.lg). Small rows, menus and inline notes use 6px (rounded.sm). Badges, confidence chips and suggestion pills are full pills (rounded.pill). The XP avatar is a 30% squircle that follows its own icon tile; people avatars and status dots are circles. The user's chat bubble has one tight corner (10px 10px 2px 10px) pointing at its sender.

Icons are line icons with a 2px stroke, drawn inline as SVG. Borders are 1px; dashed 1px marks a drop target or an empty state.

## Components

### Buttons
Quiet and solid; a small press (scale .97) on click.
- **Shape:** gently rounded (8px), 40px tall, 15px semibold text.
- **Primary:** white on Study Blue fill, a faint blue shadow; hover deepens to Pressed Study Blue.
- **Secondary:** Card White with a Hairline border and ink text; hover to Hover Slate. **Ghost** is the same without border.
- **AI:** white on the XP gradient. Only for XP actions.
- **Danger:** white on danger-fill. Only for destructive confirms.
- **Icon buttons:** 34px square (44px on phones), muted until hover.

### Chips
- **Badges:** pill, 13px bold, a soft tint with its matching text role (primary, ai, success, warning, danger, neutral). Status chips add a 6px dot.
- **Citation chips:** 6px corners, Hairline border, blue text; hover or active shifts to a blue border on Blue Wash.
- **Segmented control:** a bordered tray with a Blue Wash pill that slides to the selected option.

### Cards / Containers
- **Corner Style:** 8px for list cards and subject cards; 12px for task-framing containers.
- **Background:** Card White on Paper.
- **Shadow Strategy:** Resting (see Elevation & Depth).
- **Border:** 1px Hairline; subject cards turn the border blue and lift 2px on hover.
- **Internal Padding:** 16px for rows and cards, up to 24 to 32px for heroes and question cards.

### Inputs / Fields
- **Style:** 42px tall, 1px Hairline border, 8px corners, Card White, 15px text (16px on phones).
- **Focus:** border turns Study Blue with a 3px soft blue ring. The chat composer turns to ai-one with an XP-tinted ring.
- **Border:** form fields (inputs, selects, short answers, the chat composer) use input-border, 3:1 or more against their ground (WCAG 1.4.11); cards keep the softer border hairline.
- **Error:** border turns danger with a 14px danger-text message below.

### Navigation
- **Sidebar:** 16px nav items, 40px tall, muted until hover. The active item is blue text on a Blue Wash pill that slides between items, with a 3px blue marker at the sidebar's edge. Focus rings sit inside (offset -2px) so the clipped nav never cuts them.
- **Phone:** a five-tab bottom bar; the active tab is blue with a 2px bar on top that slides between tabs.
- **Top bar:** breadcrumb on the left, theme, notifications and account on the right.

### XP Avatar
XP's purple 3D icon on the XP gradient in a 30% squircle, 40px (32px small). It marks every place XP speaks or works.

### Answer Evidence (signature)
Directly under each XP answer: a bordered Card White figure (8px corners, 12px 14px padding). The caption reads "From **file name**" at 14px with a blue file icon. The passage is a 16px quote at 1.6 line height, clamped to three lines until the student asks for the whole passage; the words that match the answer are marked with an 18% Study Blue highlight. Every grounded answer gets one. The "Not in your materials" reply is its honest counterpart: a Blue Wash panel with an info mark and a way to add files.

## Do's and Don'ts

### Do:
- **Do** size text by role: 12 label, 13 meta, 14 UI, 16 for anything read. Nothing visible under 13px.
- **Do** put white text only on primary-fill, danger-fill or the XP gradient.
- **Do** keep the XP gradient on XP surfaces: Ask XP, the XP avatar, AI actions, the composer.
- **Do** show keyboard focus as a solid 2px focus outline with a 2px offset (inside, -2px, in the sidebar nav).
- **Do** animate with `--ease-out` (cubic-bezier(.22, 1, .36, 1)) or near-critically damped springs at 120 to 320ms, and switch motion off under `prefers-reduced-motion`.
- **Do** show the source passage under every grounded XP answer.
- **Do** check every pairing for WCAG AA in both themes.

### Don't:
- **Don't** put a kicker or eyebrow label above a heading, and don't use all-caps or tracked-out labels. Sentence case everywhere.
- **Don't** add a coloured side border thicker than 1px to a card, callout, quote or row. The sidebar's 3px active marker at the nav edge is the only edge mark.
- **Don't** use gradient text. The single background-clip text effect is the "XP is thinking…" shimmer, and it turns off under reduced motion.
- **Don't** use the purple gradient or purple washes as decoration on non-XP surfaces.
- **Don't** use primary as a fill under white text in dark theme; use primary-fill.
- **Don't** bounce, overshoot or block studying with a transition.
- **Don't** add new one-off sizes, colours or radii. Known drift to fold back into tokens, not copy: 15px text on buttons, inputs, breadcrumbs, empty states and evidence links (between the 14 and 16 roles); the file-type tile's 11px and 10px label (under the 13px floor); hard-coded XP badge purples (#6746a5, #c4b5fd) instead of ai-text; raw `.15s ease` transitions instead of `--dur-fast` and `--ease-out`; one-off radii 7px, 10px, 14px and 16px; the current landing CTA's #172554 navy.
