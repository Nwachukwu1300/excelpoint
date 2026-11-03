# ExcelPoint landing page: design context

Paste this into Claude (claude.ai) together with the brand images listed under "Assets to attach". It describes the product, the audience, the brand and exactly what the landing page must do, so the designs can be built straight into the existing app.

## What we want from you

Design the marketing landing page for ExcelPoint as working front-end code we can port into our React app: a desktop design (1440 px) and a phone design (390 px), in both light and dark themes. Show two or three distinct directions first, then refine the chosen one.

## The product in one paragraph

ExcelPoint is a free study app for school and university students. A student uploads their own class material (PDF or Word notes, or lecture recordings), and every file becomes a summary, flashcards and a quiz. **XP**, the AI study assistant, answers questions using only those files, shows the exact passage behind each answer, and says "Not in your materials" when a question isn't covered. Flashcards come back on a spaced-repetition schedule, and a Today page shows the most useful thing to study next.

**Promise:** learn faster from your own notes.

## Who it is for

- University and school students in content-heavy courses (biology, law, medicine, business) with lots of slides, notes and recorded lectures.
- Many read English as a second language, so every word on the page must be plain and literal. No idioms ("all caught up", "level up your game"), no jargon ("RAG", "embeddings", "grounded", "faithfulness").
- They have tried ChatGPT and don't fully trust it: it mixes in things their lecturer never said and makes things up.

## The page's one job

Get a visitor to sign up and upload their first file. Every section should push toward the single button **"Start studying free"**, which goes to `/app/register`.

## What the page must contain

1. **Hero:** the promise, one line on how it works, the "Start studying free" button and a "Sign in" link (`/app/login`). Use the 3D "E" icon as the hero visual, or a product moment (see 2).
2. **A live-feeling example of XP:** a real question about lecture notes, XP's answer, and the highlighted source passage it came from, labelled with the file name (for example `photosynthesis-notes.docx · part 1`) and a "Verified" check. This is the most important proof on the page.
3. **How it works, in three steps:** Upload (notes or a lecture recording) → Ask XP (answers only from your files, with sources) → Review (flashcards that come back just before you'd forget, plus quizzes).
4. **Trust:**
   - XP says "Not in your materials" instead of guessing; show that reply as a UI moment.
   - Every answer shows its source.
   - Privacy in plain words: only you can see your files; you can download or delete everything at any time; no ads, no selling data.
5. **What you get from every file:** a summary, 5 flashcards, a 10-question quiz, and chat.
6. **For the skeptic (short FAQ):** Is it free? (Yes, during the beta, no credit card.) What files work? Where do my files go? (Stored privately; their text and recordings are sent to OpenAI to write answers, and OpenAI says it doesn't train on that data.) Can I delete my data? (Yes, any time.)
7. **Final call to action**, repeated: "Start studying free".
8. **Footer:** the logo, links to Privacy (`/app/privacy`) and Terms (`/app/terms`), "Free while in beta (early testing)", © ExcelPoint, contact mnfinance664@gmail.com.

## Facts you can use (all true today)

- File types: PDF, Word (.docx), audio (MP3, WAV, M4A), video (MP4, MOV, AVI); up to 100 MB; recordings up to 3 hours.
- Each upload is ready in about 10 seconds for notes (recordings take longer) and makes a summary, 5 flashcards and a 10-question quiz.
- XP answers only from that subject's files, shows the source passage, and checks each statement against it.
- Flashcards: Again, Hard, Good, Easy. On a new card, Hard comes back in 1 day, Good in 3, Easy in 7.
- Quizzes can be saved and resumed, and you can ask for fresh questions.
- Works on phones and in light and dark themes.
- Download all your data as a zip, or delete any file, subject, chat or the whole account.
- Free while in beta. No credit card.

## Do not claim

- No user counts, ratings, testimonials, university logos or "trusted by" rows: there are no public users yet.
- No percentages or "X times faster" numbers.
- Don't say "never wrong": XP can still make mistakes, it just shows its sources so you can check.
- Don't call XP a tutor or teacher; it's an "AI study assistant".
- Don't mention GPT model names; "OpenAI" is fine where privacy is explained.

## Brand

**Names**

- **ExcelPoint** is the product. The wordmark is "Excel**P**oint": Inter, weight 800 to 900, tight letter-spacing (about -0.045em), dark navy, with the **P in brand blue**.
- **XP** is the AI assistant inside ExcelPoint. Only XP surfaces use the purple gradient.

**Logos**

- ExcelPoint icon: a 3D glass letter "E" made of three stacked glowing blue slabs, the top one ending in an arrow point, on deep navy.
- XP icon: a 3D frosted purple rounded square with white "XP" letters and a small glowing spark.

**Colours** (use these exact values as CSS custom properties)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--primary` | `#2563EB` | `#3B82F6` | brand blue: buttons, links, the P |
| `--primary-hover` | `#1D4ED8` | `#60A5FA` | hover |
| `--ai-one` → `--ai-two` | `#667EEA` → `#764BA2` | same | the XP gradient, only on XP and AI moments |
| `--success` | `#06A77F` | `#06D6A0` | "Verified" |
| `--warning` | `#D97706` | `#F59E0B` | warnings |
| `--danger` | `#EF4444` | `#EF4444` | errors |
| `--text` | `#1E293B` | `#F1F5F9` | text |
| `--muted` | `#64748B` | `#94A3B8` | secondary text |
| `--border` | `#E2E8F0` | `#334155` | borders |
| `--background` | `#F8FAFC` | `#0F172A` | page |
| `--card` | `#FFFFFF` | `#1E293B` | cards |

**Type:** Inter (Google Fonts), 400 to 900. Large bold headings with tight tracking; body 16 to 18 px on the landing page.

**Shape and feel:** clean and focused, like Linear or Notion, with 8 px corners on UI, subtle shadows and generous white space. The 3D logos bring the "wow"; everything around them stays calm. Avoid generic AI-startup looks: purple-to-blue gradient heroes on white, emoji icons, stock illustrations of students.

**Motion:** calm and fast. One orchestrated moment is fine, such as XP's answer streaming in and the source highlighting. Respect `prefers-reduced-motion`, and keep every word readable on first load with no scroll-triggered fade-ins that hide content. Inspiration for components and motion: https://bencho.dev/ and https://easyui.site/.

## Technical constraints (so we can port it)

- The app is React 19 + TypeScript with React Router 7 and Motion (the `motion/react` package), styled with **plain CSS and CSS custom properties, not Tailwind**. Write the design as React components with a plain CSS file, or as a single HTML file with plain CSS we can convert. Name tokens as in the table above.
- Light and dark themes: the app sets `data-theme="light"` or `data-theme="dark"` on `<html>`, and falls back to `prefers-color-scheme`.
- It must load fast on a phone over slow 3G: no heavy images beyond the two logos and one product shot, no video backgrounds, and no extra web-font families beyond Inter.
- Links: sign up `/app/register`, sign in `/app/login`, Privacy `/app/privacy`, Terms `/app/terms`.
- Accessible: real headings in order, visible focus states, AA contrast in both themes, and alt text on the logos.
- Widths: desktop 1440 with a content max of about 1120, and phone 390 with 16 px side padding and no sideways scrolling.

## Assets to attach

From the `branding/` folder of the repo:

- `branding/excelpoint-3d-app-icon-e.png`: the ExcelPoint 3D "E" (1024 × 1024, on navy)
- `branding/xp-3d-mascot-app-icon.png`: the XP icon (1024 × 1024, on navy)
- `branding/link-preview-1200x630.png`: the shared-link card, showing the brand together

Optional: screenshots of the real app (chat with sources, the Today page, a flashcard) for the product shot.

## The current page, to replace

`/app/welcome` today has a nav with the logo, a centred hero ("Learn faster from your own materials", "Start studying free" and "Sign in"), a small mock of an XP answer, a three-step "How it works", a feature grid, a closing call to action and a footer. It is correct but plain, and it doesn't sell. The new page should feel premium and make the XP-answer-with-source moment the centrepiece.
