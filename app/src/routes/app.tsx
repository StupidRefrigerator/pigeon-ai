import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/app')({ component: AppShell })

function AppShell() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Pigeon AI
        </Link>
        <Link to="/app" activeOptions={{ exact: true }} activeProps={{ className: 'active' }}>
          App
        </Link>
        <Link to="/app/stats" activeProps={{ className: 'active' }}>
          Stats
        </Link>
      </header>
      <div className="page">
        <Outlet />
      </div>
    </div>
  )
}
