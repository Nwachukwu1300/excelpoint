import { Fragment, type ReactNode } from 'react'

type Block =
  | { type: 'p'; text: string }
  | { type: 'h'; text: string }
  | { type: 'ul' | 'ol'; items: string[] }
  | { type: 'code'; text: string }

/** Split answer text into blocks. Tolerates a half-written answer while it streams (e.g. an unclosed code fence). */
export function parseBlocks(text: string): Block[] {
  const blocks: Block[] = []
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  let i = 0
  while (i < lines.length) {
    const line = lines[i]!
    if (line.trim().startsWith('```')) {
      const code: string[] = []
      i++
      while (i < lines.length && !lines[i]!.trim().startsWith('```')) code.push(lines[i++]!)
      i++ // closing fence (may not have arrived yet)
      blocks.push({ type: 'code', text: code.join('\n') })
      continue
    }
    const bullet = /^\s*[-*•]\s+(.*)$/
    const numbered = /^\s*\d+[.)]\s+(.*)$/
    if (bullet.test(line) || numbered.test(line)) {
      const pattern = bullet.test(line) ? bullet : numbered
      const items: string[] = []
      while (i < lines.length && pattern.test(lines[i]!)) items.push(lines[i++]!.match(pattern)![1]!)
      blocks.push({ type: pattern === bullet ? 'ul' : 'ol', items })
      continue
    }
    const heading = line.match(/^#{1,6}\s+(.*)$/)
    if (heading) { blocks.push({ type: 'h', text: heading[1]! }); i++; continue }
    if (!line.trim()) { i++; continue }
    const para: string[] = []
    while (i < lines.length && lines[i]!.trim() && !/^\s*([-*•]|\d+[.)]|#{1,6})\s+|^\s*```/.test(lines[i]!)) para.push(lines[i++]!.trim())
    blocks.push({ type: 'p', text: para.join(' ') })
  }
  return blocks
}

/** **bold**, *italic* / _italic_ and `code`, as React elements (never innerHTML). */
export function inline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const pattern = /(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*\s][^*]*)\*|_([^_\s][^_]*)_)/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = pattern.exec(text))) {
    if (match.index > last) out.push(text.slice(last, match.index))
    const [, , bold, code, em1, em2] = match
    const key = match.index
    if (bold) out.push(<strong key={key}>{bold}</strong>)
    else if (code) out.push(<code key={key}>{code}</code>)
    else out.push(<em key={key}>{em1 ?? em2}</em>)
    last = match.index + match[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

/** Answer text as paragraphs, lists and code. `caret` shows the streaming cursor after the last block. */
export function Markdown({ text, caret }: { text: string; caret?: ReactNode }) {
  const blocks = parseBlocks(text)
  const end = (i: number) => (i === blocks.length - 1 ? caret : null)
  return (
    <>
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'code': return <Fragment key={i}><pre><code>{b.text}</code></pre>{end(i)}</Fragment>
          case 'h': return <p key={i}><strong>{inline(b.text)}</strong>{end(i)}</p>
          case 'ul': case 'ol': {
            const List = b.type
            return <List key={i}>{b.items.map((item, j) => <li key={j}>{inline(item)}{j === b.items.length - 1 ? end(i) : null}</li>)}</List>
          }
          default: return <p key={i}>{inline(b.text)}{end(i)}</p>
        }
      })}
      {blocks.length === 0 && caret}
    </>
  )
}
