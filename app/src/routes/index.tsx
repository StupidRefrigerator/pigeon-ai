import { Link, createFileRoute } from '@tanstack/react-router'
import { AuthControls } from '../components/AuthControls'

export const Route = createFileRoute('/')({ component: Landing })

function Landing() {
  return (
    <main className="landing">
      <h1>Pigeon AI</h1>
      <p className="tagline">Helping councils plan where Sydney's next public toilets should go.</p>
      <span className="badge">Coming soon</span>
      <div className="actions">
        <AuthControls />
        <Link to="/app" className="btn ghost">
          Open the app
        </Link>
      </div>
    </main>
  )
}
