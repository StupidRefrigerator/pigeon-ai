import { useId, useState, type ReactNode } from 'react'
import { DEFINITIONS, type TermId } from '../lib/definitions'

/**
 * A term with a dotted underline that shows its definition on hover or keyboard focus.
 * CSS shows the popover; the handler only pins it under the term with fixed positioning,
 * so table scroll areas do not clip it. The title attribute is the no-CSS fallback.
 */
export function Term({ id, children }: { id: TermId; children: ReactNode }) {
  const tipId = useId()
  const [pos, setPos] = useState<{ left: number; top: number }>()
  const place = (el: HTMLElement) => {
    const r = el.getBoundingClientRect()
    setPos({ left: Math.max(8, Math.min(r.left, window.innerWidth - 328)), top: r.bottom + 6 })
  }
  return (
    <span className="term-wrap">
      <span
        className="term"
        tabIndex={0}
        title={DEFINITIONS[id]}
        aria-describedby={tipId}
        onPointerEnter={(e) => place(e.currentTarget)}
        onFocus={(e) => place(e.currentTarget)}
        onKeyDown={(e) => e.key === 'Escape' && e.currentTarget.blur()}
      >
        {children}
      </span>
      <span role="tooltip" id={tipId} className="term-tip" style={pos}>
        {DEFINITIONS[id]}
      </span>
    </span>
  )
}
