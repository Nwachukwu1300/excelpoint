const COLORS = ['violet', 'blue', 'green'] as const

export const subjectInitials = (name: string) => {
  const words = name.trim().split(/\s+/)
  return (words.length > 1 ? words[0]![0]! + words[1]![0]! : name.slice(0, 2)).toUpperCase()
}

/** Coloured initials tile; the colour is stable per subject id. */
export function SubjectIcon({ id, name }: { id: number; name: string }) {
  return <span className={`subject-icon subject-icon--${COLORS[id % COLORS.length]}`} aria-hidden="true">{subjectInitials(name)}</span>
}
