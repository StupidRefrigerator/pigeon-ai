import { Show, SignInButton, UserButton } from '@clerk/tanstack-react-start'
import { Link, Outlet, createFileRoute, useRouterState } from '@tanstack/react-router'
import { useState, type CSSProperties } from 'react'
import { clerkEnabled } from '../lib/clerk'
import '../shell.css'

export const Route = createFileRoute('/app')({ component: AppShell })

const INFRA = [
  { name: 'Toilets', color: '#FF48B0', live: true },
  { name: 'Bike lanes', color: '#FFE800', live: false },
  { name: 'Water fountains', color: '#3255A4', live: false },
  { name: 'Shade trees', color: '#321871', live: false },
] as const

const ADMIN_PAGES: Record<string, string> = { '/app/stats': 'Tracking', '/app/tests': 'Tests' }

function AppShell() {
  const path = useRouterState({ select: (s) => s.location.pathname.replace(/\/$/, '') })
  const adminPage = ADMIN_PAGES[path]
  const [adminOpen, setAdminOpen] = useState(true)

  return (
    <div className="dash">
      <aside className="dash-side">
        <div className="dash-brand">
          <Link to="/" className="dash-home" aria-label="Pigeon AI home">
            <Logo />
            <span className="dash-word">PIGEON AI</span>
          </Link>
          <span className="dash-wip" title="Features and numbers on these pages may change">
            Work in progress
          </span>
        </div>

        <div className="dash-group">
          <div className="dash-group-h" id="infra-h">
            Infrastructure
          </div>
          <ul className="dash-infra" aria-labelledby="infra-h">
            {INFRA.map((i) => (
              <li key={i.name} className={i.live ? 'live' : 'soon'} style={{ '--c': i.color } as CSSProperties} aria-current={i.live ? 'true' : undefined}>
                <i className="swatch" aria-hidden="true" />
                {i.name}
                <small>{i.live ? 'live' : 'soon'}</small>
              </li>
            ))}
          </ul>
        </div>

        <nav className="dash-nav" aria-label="Main">
          <Link to="/app" activeOptions={{ exact: true }}>
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
            <Link to="/app/stats">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 20h18M6 16V9M11 16V5M16 16v-4M21 16V8" />
              </svg>
              Tracking
            </Link>
            <Link to="/app/tests">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" />
              </svg>
              Tests
            </Link>
          </div>
        </nav>

        <UserMenu />
      </aside>

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

function UserMenu() {
  if (!clerkEnabled) {
    return (
      <div className="dash-me">
        <span className="dash-av" aria-hidden="true">
          ?
        </span>
        <div className="dash-me-text">
          <b>Sign-in is off</b>
          <span>Clerk keys are not set</span>
        </div>
      </div>
    )
  }
  return (
    <div className="dash-me">
      <Show when="signed-in">
        <UserButton showName />
      </Show>
      <Show when="signed-out">
        <SignInButton>
          <button className="dash-signin">Sign in</button>
        </SignInButton>
      </Show>
    </div>
  )
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
