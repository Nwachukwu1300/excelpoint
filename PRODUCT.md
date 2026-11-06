# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Students at university and at school, equally, anywhere English is the language of study. Neither group comes first, so copy, examples and flows must work for a 15-year-old revising for a school exam and for a university student revising a course.

Their situation: each course leaves them with a pile of material (lecture slides, notes, handouts, recorded lectures) and an exam to pass. The job is to learn and remember that specific material, quickly, without re-reading everything or hand-writing flashcards.

Many read English as a second language and follow the interface literally. Many study on a phone, often on a slow connection. Most have tried general AI chatbots and don't fully trust them: those answer from everything, mix in things the teacher never said, make things up and rarely show a source.

## Product Purpose

ExcelPoint turns a student's own course material into a study system. Every uploaded file (PDF, Word, or an audio or video recording) becomes a summary, flashcards and a quiz. XP, the AI study assistant, answers questions from those files, and a Today page shows the most useful thing to study next.

Success means a student gets a sourced answer about their own notes in their first session, and keeps coming back to review until the exam.

## Positioning

XP answers only from the student's own files and shows the exact passage behind every answer. When something isn't covered, it says "Not in your materials" instead of guessing. Every file becomes a study loop without the student doing anything: summary, flashcards on a spaced-repetition schedule, quiz, and the Today queue. (Confirmed 2026-11-03.)

General chatbots cannot truthfully claim the first half. Flashcard and quiz apps cannot claim the second.

## Operating Context

- **Material:** lecture slides and notes as PDF or Word (.docx), and lecture recordings (MP3, WAV, M4A, MP4, MOV, AVI); up to 100 MB per file, recordings up to 3 hours. Scanned pages without text can't be read yet.
- **Subjects:** a student organises material into subjects, one per class or topic.
- **Rituals:**
  - a daily review of flashcards that are due, graded Again, Hard, Good or Easy;
  - asking XP while studying;
  - taking and resuming quizzes;
  - explaining a topic back to XP, out loud or typed, and seeing each statement marked against their notes;
  - checking the Coverage map to see which parts of their files are solid, shaky, fading or not studied, and studying a gap straight from it;
  - "How was this answered?" to check an answer.
- **Devices:** phones and laptops, in light and dark themes.

## Capabilities and Constraints

- **Grounding:** XP replies "Not in your materials", with no AI call, when nothing in the subject's files is close enough. Answers stream in with their source passages and a check of each statement.
- **Explain it back:** the student explains a topic or file; XP marks each statement Correct, Not quite (with the passage that shows the right answer) or Not in your notes (never wrong just because the notes are silent), lists key points they missed, replies in under 20 seconds of speech, and ends with coverage and accuracy. Only the transcript is kept, never the recording.
- **Coverage map:** one number and one sentence per subject ("You've studied 62% of Biology. Chapter 4 hasn't come up yet.") and every section of every file marked Not studied, Shaky, Solid or Fading, always with a label and icon, never colour alone. Explain it back is the strongest signal. The map is worked out from what the student did, so it updates as soon as they study.
- **Background work:** processing runs in the background, and the student gets a notification when a file is ready or can't be read, with the reason.
- **Account:** password reset by email, Google sign-in when configured, download all data as a zip, and delete any file, subject, conversation or the whole account.
- **Price:** free while in beta, with no credit card. Pricing after the beta is undecided.
- **AI provider:** OpenAI writes answers and study aids and transcribes recordings. XP's spoken replies use the device's own voice by default (OpenAI's voice is a setting). Search runs on ExcelPoint's own server.
- **Limits:** 60 questions per student per hour; 30 Explain it back checks per student per 24 hours; recordings up to 3 hours (explanations up to 3 minutes). There is no daily upload limit yet.
- **Terminology** (use these words, one name per thing):
  - Subject, Files, Flashcards, Quiz, Home, XP.
  - "To review", not "due".
  - Avoid "caught up", "grounded", "faithfulness", "course materials".
- **Undecided:** pricing after the beta, the first target courses or institutions, and the domain name.

## Brand Commitments

- **Names:** ExcelPoint is the product. XP is the AI study assistant inside it, always described as "your AI study assistant", never a tutor or teacher.
- **Assets:** originals are in `branding/`.
  - ExcelPoint is the 3D glass "E" icon (`branding/excelpoint-3d-app-icon-e.png`) plus the wordmark "Excel**P**oint", with the P in brand blue.
  - XP is the purple 3D "XP" icon (`branding/xp-3d-mascot-app-icon.png`).
  - The shared-link card is `branding/link-preview-1200x630.png`.
  - The stacked-layers lockup in `branding/` is not used.
- **Colours:**
  - brand blue `#2563EB`;
  - the purple gradient `#667EEA` → `#764BA2`, only on XP and AI moments;
  - Inter as the typeface.
- **Voice:** plain, literal, calm and short, in British spelling ("summarise"). Errors say what happened and what to do next.

## Evidence on Hand

- **The working product,** with 304 backend and 81 app tests.
- **Launch QA:** two rounds with five simulated first-time users (impatient, skeptic, mobile on slow 3G, non-native reader, breaker). In the second round all five reached a sourced answer in about 2 minutes. Reports are in the session scratchpad and are not committed.
- **Documents:**
  - the product brief at https://claude.ai/artifact/76HBvLPusaVo8TZEcE9FTm;
  - the landing page brief at `docs/landing-page-context.md`;
  - the Privacy and Terms pages at `/app/privacy` and `/app/terms`.
- **A demo video** from an earlier version of the app: https://drive.google.com/file/d/1yBZ8Cexa4Lhrnot7D3OiEqdqtsfgFxn5/view
- **Absent, and never to be fabricated:**
  - real users, usage numbers, testimonials, ratings, institution logos or press;
  - accuracy or speed percentages;
  - pricing tiers.

## Product Principles

1. **Answers you can check beat answers that sound good.** Show the source, say when something isn't covered, and never present a guess as fact.
2. **The student owns their work.** Files stay private, can be downloaded at any time, and are gone for good when deleted. No ads, no selling data, no tracking.
3. **Plain words for every reader.** A second-language reader following the screen literally must never be lost.
4. **Calm and fast.** Studying shouldn't feel slow or noisy, including on a cheap phone on a slow connection.
5. **Study, not chat.** Every feature must help a student learn and remember their own material.

## Accessibility & Inclusion

- **Language:** plain English for second-language readers, with no idioms or jargon.
- **Phones:** text inputs at least 16 px, touch targets at least 44 px, no sideways scrolling at 375 px, and fast on slow 3G.
- **Contrast and themes:** WCAG AA contrast in both light and dark themes, and visible keyboard focus.
- **Motion:** respect `prefers-reduced-motion`; nothing blocks while it animates.
