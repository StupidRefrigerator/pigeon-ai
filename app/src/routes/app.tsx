import { Link, Outlet, createFileRoute, useRouterState } from '@tanstack/react-router'
import { useEffect, useState, type CSSProperties } from 'react'
import { DEFAULT_LAYER, LAYERS, LIVE_LAYERS, resolveLayer, type LiveLayerId } from '../infra'
import { LayerProvider, useLayer } from '../layer'
import '../shell.css'

/** `?layer=` picks the infrastructure layer; absent or unknown ids mean the default layer. */
function validateSearch(search: Record<string, unknown>): { layer?: LiveLayerId } {
  const layer = LIVE_LAYERS.find((l) => l.id === search.layer)
  return layer ? { layer: layer.id } : {}
}

export const Route = createFileRoute('/app')({ validateSearch, component: AppShell })

const ADMIN_PAGES: Record<string, string> = { '/app/stats': 'Tracking', '/app/tests': 'Tests' }

function AppShell() {
  return (
    <LayerProvider value={resolveLayer(Route.useSearch().layer)}>
      <Dashboard />
    </LayerProvider>
  )
}

function Dashboard() {
  const layer = useLayer()
  const path = useRouterState({ select: (s) => s.location.pathname.replace(/\/$/, '') })
  const adminPage = ADMIN_PAGES[path]
  const [adminOpen, setAdminOpen] = useState(true)
  const [folded, setFolded] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const narrow = useNarrow()
  const href = useRouterState({ select: (s) => s.location.href })

  useEffect(() => {
    setFolded(localStorage.getItem('pigeon-sidebar') === 'folded')
  }, [])
  useEffect(() => {
    localStorage.setItem('pigeon-sidebar', folded ? 'folded' : 'open')
  }, [folded])
  // Picking a layer or a page closes the phone menu.
  useEffect(() => setMenuOpen(false), [href])

  return (
    <div className={['dash', folded && !narrow && 'folded', menuOpen && 'menu-open'].filter(Boolean).join(' ')}>
      <aside className="dash-side" id="dash-side" inert={folded && !narrow}>
        <div className="dash-brand">
          <Link to="/" className="dash-home" aria-label="Pigeon AI home">
            <Logo />
            <span className="dash-word">PIGEON AI</span>
          </Link>
          <span className="dash-current" style={{ '--c': layer.color } as CSSProperties}>
            <i className="swatch" aria-hidden="true" />
            {layer.name}
          </span>
          <button className="dash-menu" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-controls="dash-panel" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d={menuOpen ? 'M6 6l12 12M18 6 6 18' : 'M4 7h16M4 12h16M4 17h16'} />
            </svg>
          </button>
          <button className="dash-fold" aria-label="Hide sidebar" aria-controls="dash-side" aria-expanded="true" onClick={() => setFolded(true)}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m15 6-6 6 6 6" />
            </svg>
          </button>
        </div>

        <div className="dash-panel" id="dash-panel">
        <div className="dash-group">
          <div className="dash-group-h" id="infra-h">
            Infrastructure
          </div>
          <ul className="dash-infra" aria-labelledby="infra-h">
            {LAYERS.map((i) => (
              <li key={i.id} className={i.live ? 'live' : 'soon'} style={{ '--c': i.color } as CSSProperties}>
                {i.live ? (
                  <Link to="." search={(prev) => ({ ...prev, layer: i.id === DEFAULT_LAYER.id ? undefined : i.id })} activeOptions={{ includeSearch: true, explicitUndefined: true }} aria-current={i.id === layer.id ? 'true' : undefined}>
                    <i className="swatch" aria-hidden="true" />
                    {i.name}
                    <small>live</small>
                  </Link>
                ) : (
                  <span>
                    <i className="swatch" aria-hidden="true" />
                    {i.name}
                    <small>soon</small>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <nav className="dash-nav" aria-label="Main">
          <Link to="/app" search={(prev) => prev} activeOptions={{ exact: true }}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 2 21 7v10l-9 5-9-5V7z" />
              <path d="M12 7 16.5 9.5v5L12 17l-4.5-2.5v-5z" />
            </svg>
            Map
          </Link>
          <button className="dash-admin-h" aria-expanded={adminOpen} aria-controls="admin-links" onClick={() => setAdminOpen(!adminOpen)}>
            Admin
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>
          <div id="admin-links" className="dash-admin" hidden={!adminOpen}>
            <Link to="/app/stats" search={(prev) => prev}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 20h18M6 16V9M11 16V5M16 16v-4M21 16V8" />
              </svg>
              Tracking
            </Link>
            <Link to="/app/tests" search={(prev) => prev}>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" />
              </svg>
              Tests
            </Link>
          </div>
        </nav>
        </div>
      </aside>

      {folded && (
        <button className="dash-unfold" aria-label="Show sidebar" aria-controls="dash-side" aria-expanded="false" onClick={() => setFolded(false)}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m9 6 6 6-6 6" />
          </svg>
        </button>
      )}
      <main className="dash-main">
        {adminPage ? (
          <div className="dash-admin-page">
            <p className="dash-crumb">
              Admin / <b>{adminPage}</b>
            </p>
            <div className="dash-sheet">
              <Outlet />
            </div>
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  )
}


/** True on phone-width screens, where the sidebar becomes a top bar with a menu. */
function useNarrow() {
  const [narrow, setNarrow] = useState(false)
  useEffect(() => {
    const mq = matchMedia('(max-width: 900px)')
    const update = () => setNarrow(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return narrow
}

function Logo() {
  return (
    <svg className="dash-logo" viewBox="0 0 100 120" aria-hidden="true">
      <path d="M50 6 L92 30 L92 76 L50 114 L8 76 L8 30 Z" fill="#3255A4" stroke="#3255A4" strokeWidth="8" strokeLinejoin="round" />
      <g fill="#FFE800" transform="translate(14 16) scale(0.72)">
        <path d="M45 38 Q26 26 2 34 L8 40 L3 46 L10 50 L6 56 Q28 62 45 58 Z" />
        <path d="M55 38 Q74 26 98 34 L92 40 L97 46 L90 50 L94 56 Q72 62 55 58 Z" />
        <ellipse cx="50" cy="50" rx="9" ry="20" />
        <circle cx="50" cy="27" r="7" />
        <polygon points="47.5,22 50,15 52.5,22" />
        <path d="M44.5 66 L38 87 Q50 92 62 87 L55.5 66 Z" />
      </g>
    </svg>
  )
}
