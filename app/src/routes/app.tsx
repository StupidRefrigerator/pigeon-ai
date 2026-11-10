import { Link, Outlet, createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/app')({ component: AppShell })

function AppShell() {
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <img src="/logo.svg" alt="" />
          Pigeon AI
        </Link>
        <Link to="/app" activeOptions={{ exact: true }} activeProps={{ className: 'active' }}>
          App
        </Link>
        <Link to="/app/stats" activeProps={{ className: 'active' }}>
          Tracking
        </Link>
        <Link to="/app/tests" activeProps={{ className: 'active' }}>
          Tests
        </Link>
      </header>
      <div className="page">
        <Outlet />
      </div>
    </div>
  )
}
