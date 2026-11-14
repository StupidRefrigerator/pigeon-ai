import { useEffect, useRef } from 'react'

/** Side panel for the assistant. Closed by default; the assistant itself is not connected yet. */
export function AskPanel({ open, onToggle }: { open: boolean; onToggle: (open: boolean) => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const openRef = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(open)
  useEffect(() => {
    if (open) closeRef.current?.focus()
    else if (wasOpen.current) openRef.current?.focus()
    wasOpen.current = open
  }, [open])

  return (
    <>
      <button ref={openRef} className="ask-toggle slab" aria-expanded={open} aria-controls="ask-panel" hidden={open} onClick={() => onToggle(true)}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 5h16v11H9l-5 4z" />
        </svg>
        Ask Pigeon
      </button>
      <aside id="ask-panel" className="ask-panel" aria-labelledby="ask-title" hidden={!open}>
        <header>
          <h2 id="ask-title">Ask Pigeon</h2>
          <button ref={closeRef} className="ask-close" onClick={() => onToggle(false)}>
            Close
          </button>
        </header>
        <div className="ask-body">
          <p className="ask-soon">Ask Pigeon — coming soon</p>
          <p>You will be able to ask about any suburb or suggested spot, and the answer will point to the hexagons on the map.</p>
        </div>
        <form className="ask-composer" onSubmit={(e) => e.preventDefault()}>
          <input placeholder="Why is Woolloomooloo short of toilets?" aria-label="Question" disabled />
          <button disabled>Ask</button>
        </form>
      </aside>
    </>
  )
}
