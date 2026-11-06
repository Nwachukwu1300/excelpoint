import { Link } from 'react-router'
import { Logo } from '../../ui/primitives'
import '../../styles/auth.css'

export const CONTACT = 'mnfinance664@gmail.com'
const UPDATED = '6 November 2026'

type Sections = [string, string[]][]

/** Privacy and Terms share this layout: plain headed lists, with links between them. */
export function LegalPage({ title, intro, sections }: { title: string; intro: string; sections: Sections }) {
  return (
    <main className="auth-page privacy-page">
      <Link className="auth-logo" to="/welcome" aria-label="ExcelPoint home"><Logo /></Link>
      <article className="auth-card privacy-card">
        <h1>{title}</h1>
        <p className="privacy-updated">{intro} Last updated {UPDATED}.</p>
        {sections.map(([heading, points]) => (
          <section key={heading}>
            <h2>{heading}</h2>
            <ul>{points.map(p => <li key={p}>{p}</li>)}</ul>
          </section>
        ))}
        <section>
          <h2>Contact</h2>
          <ul><li>Questions, requests or complaints: <a href={`mailto:${CONTACT}`}>{CONTACT}</a></li></ul>
        </section>
        <p className="auth-switch">
          <Link to="/privacy">Privacy</Link> · <Link to="/terms">Terms</Link> · <Link to="/register">Create an account</Link> · <Link to="/welcome">Home page</Link>
        </p>
      </article>
    </main>
  )
}

// Describes what the code does today. Update it whenever data handling changes.
const PRIVACY: Sections = [
  ['What we keep', [
    'Your account: username, email, password (stored scrambled, never readable), and the name and level of education you choose to add.',
    'Your files, the text read from them, and the summaries, flashcards and quizzes made from them.',
    'Your questions to XP, its answers, and a record of how each answer was made (which parts of your files it used, and quality scores).',
    'Your quiz answers, flashcard review history and notifications.',
    'The Coverage map: how each file is split into sections and their names. Which sections you’ve studied is worked out from your reviews, quizzes and explanations each time you look, not stored separately.',
    'Explain it back sessions: the topic, what you said or typed (as text), XP’s feedback and replies, your scores, and a record of how each check was made. We never keep your voice recordings.',
  ]],
  ['Who can see it', [
    'Only you. Other people using ExcelPoint can’t see your files, questions or results.',
    'To write answers, summaries, flashcards and quizzes, the text of your files and your questions is sent to OpenAI, the company that runs the AI model XP uses.',
    'Audio and video recordings are sent to OpenAI to be turned into text. We keep the text and your original file, not a separate audio copy.',
    'When you explain a topic out loud, the recording is sent to OpenAI to be turned into text, then thrown away. Only the text is kept.',
    'To name the sections of your Coverage map, the start of each untitled section is sent to OpenAI once, when the file is processed.',
    'XP’s spoken replies are read out by your device’s own voice. If we switch to OpenAI’s voice, the text of XP’s reply (never your recording) is sent to OpenAI to make the audio.',
    'OpenAI says it does not use data sent through its API to train its models, and keeps it for up to 30 days to check for abuse before deleting it.',
    'The search that finds the right parts of your files runs on our own server.',
    'If you sign in with Google, Google tells us your name, email address and Google account ID.',
  ]],
  ['How long we keep it', [
    'Everything stays until you delete it, or until you delete your account.',
    'Deleting a file, subject, conversation, Explain it back session or your account removes it from our database and file storage straight away. Deleting a file also removes its sections from your Coverage map.',
    'We keep a backup copy of the database each night for 7 days, so anything you delete is gone from the backups within 7 days.',
  ]],
  ['What we don’t do', [
    'No ads, no selling your data, and no marketing email.',
    'No tracking or analytics tools. The site uses only the cookies it needs to keep you signed in and protect forms, and remembers your light or dark theme, and whether XP’s voice is off, in your browser.',
  ]],
  ['Your choices', [
    'Settings → Download my data gives you a zip of your files and everything made from them, including your Coverage map and Explain it back sessions.',
    'You can delete any file, subject, XP conversation or Explain it back session at any time.',
    'Explain it back works without a microphone: you can always type instead.',
    'Settings → Delete account removes your account and everything above, including your stored files. This can’t be undone.',
  ]],
  ['Price', [
    'ExcelPoint is free while it is in beta (early testing).',
  ]],
]

export function Privacy() {
  return <LegalPage title="Privacy" intro="How ExcelPoint handles your data, in plain words." sections={PRIVACY} />
}
