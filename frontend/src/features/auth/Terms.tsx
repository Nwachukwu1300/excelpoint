import { LegalPage } from './Privacy'

const TERMS: [string, string[]][] = [
  ['About ExcelPoint', [
    'ExcelPoint (“we”) is a study app: you upload your class files, and XP, an AI study assistant, answers questions about them and makes summaries, flashcards and quizzes.',
    'By creating an account or using ExcelPoint, you agree to these terms and to how we handle data, as described on the Privacy page.',
  ]],
  ['Your account', [
    'You must be at least 13 years old to use ExcelPoint.',
    'Keep your password to yourself. You are responsible for what happens in your account.',
    'One account per person and per email address.',
  ]],
  ['Your files', [
    'Your files stay yours. You give us permission to store and process them, including sending their text to OpenAI, only so that ExcelPoint can work for you.',
    'Only upload files you have the right to use, such as your own notes or materials your course lets you use for study.',
    'We don’t use your files for anything else, and we don’t share them with other users.',
  ]],
  ['Fair use', [
    'Don’t upload anything illegal or harmful, or files that contain malware.',
    'Don’t try to break, overload or get around the limits of the service, or get into other people’s accounts or data.',
    'We limit how many questions XP answers per hour so the service stays available to everyone.',
  ]],
  ['XP’s answers', [
    'XP answers only from your files, but it is an AI and can still be wrong or leave things out. Check anything important against your files or your teacher.',
    'Nothing XP says is professional advice (medical, legal, financial or otherwise).',
  ]],
  ['A free beta', [
    'ExcelPoint is free while it is in beta (early testing). Features may change, and parts of it may be unavailable at times.',
    'If we decide to close ExcelPoint, we will try to give notice on the site so you can download your data first.',
  ]],
  ['Ending your use', [
    'You can stop at any time and delete your account in Settings.',
    'We may suspend or close an account that breaks these terms.',
  ]],
  ['Our responsibility', [
    'ExcelPoint is provided “as is”. As far as the law allows, we are not responsible for indirect losses, such as lost marks or lost time, or for files you didn’t keep a copy of elsewhere.',
    'Nothing in these terms limits any rights you have by law that can’t be limited, or our responsibility for death or personal injury caused by our negligence, or for fraud.',
  ]],
  ['Changes and law', [
    'We may update these terms. The date at the top shows the latest version; if you keep using ExcelPoint after a change, the new terms apply.',
    'These terms are governed by the law of England and Wales, and disputes go to its courts. If you live in Scotland or Northern Ireland, you can also use your local courts.',
  ]],
]

export function Terms() {
  return <LegalPage title="Terms" intro="The rules for using ExcelPoint, in plain words." sections={TERMS} />
}
