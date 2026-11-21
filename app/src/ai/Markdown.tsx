import { Fragment, type ReactNode } from 'react'

const INLINE = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)\s]+\)|`[^`]+`)/g

function inline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <b key={i}>{part.slice(2, -2)}</b>
    if (part.startsWith('`') && part.endsWith('`')) return <code key={i}>{part.slice(1, -1)}</code>
    const link = part.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/)
    if (link && /^https?:\/\//.test(link[2]!)) {
      return (
        <a key={i} href={link[2]} target="_blank" rel="noreferrer">
          {link[1]}
        </a>
      )
    }
    return <Fragment key={i}>{part}</Fragment>
  })
}

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/

/** OpenAI's inline citation markers (private-use characters around "cite…"); the sources are linked in the text already. */
const CITE = /\ue200[^\ue201]*(?:\ue201|$)/g

/** The little Markdown the assistant writes: paragraphs, bullet or numbered lists, headings, bold, code and links. */
export function Markdown({ text }: { text: string }) {
  const blocks = text.replace(CITE, '').trim().split(/\n{2,}/)
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split('\n').filter((l) => l.trim())
        if (lines.length && lines.every((l) => BULLET.test(l))) {
          const Tag = /^\s*\d/.test(lines[0]!) ? 'ol' : 'ul'
          return (
            <Tag key={i}>
              {lines.map((l, k) => (
                <li key={k}>{inline(l.replace(BULLET, ''))}</li>
              ))}
            </Tag>
          )
        }
        const heading = block.match(/^#{1,4}\s+(.*)$/)
        if (heading && lines.length === 1) return <h4 key={i}>{inline(heading[1]!)}</h4>
        return (
          <p key={i}>
            {lines.map((l, k) => (
              <Fragment key={k}>
                {k > 0 && <br />}
                {inline(BULLET.test(l) ? `• ${l.replace(BULLET, '')}` : l)}
              </Fragment>
            ))}
          </p>
        )
      })}
    </>
  )
}
