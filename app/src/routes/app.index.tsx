import { createFileRoute } from '@tanstack/react-router'
import { AuthControls } from '../components/AuthControls'

export const Route = createFileRoute('/app/')({ component: AppHome })

function AppHome() {
  return (
    <section className="placeholder">
      <h1>Pigeon AI app</h1>
      <p>Coming soon.</p>
      <AuthControls />
    </section>
  )
}
