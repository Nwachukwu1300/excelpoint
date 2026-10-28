const COLORS = ['violet', 'blue', 'green'] as const

// Whole characters (not UTF-16 halves), letters and digits only, so an emoji can't come out as "�"
const letters = (word: string) => [...word].filter(c => /[\p{L}\p{N}]/u.test(c))

export const subjectInitials = (name: string) => {
  const words = name.trim().split(/\s+/).map(letters).filter(w => w.length)
  const picked = words.length > 1 ? [words[0]![0], words[1]![0]] : (words[0] ?? []).slice(0, 2)
  return picked.join('').toUpperCase() || '?'
}

/** Coloured initials tile; the colour is stable per subject id. */
export function SubjectIcon({ id, name }: { id: number; name: string }) {
  return <span className={`subject-icon subject-icon--${COLORS[id % COLORS.length]}`} aria-hidden="true">{subjectInitials(name)}</span>
}
