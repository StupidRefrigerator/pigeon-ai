import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/app/')({ component: AppHome })

function AppHome() {
  return (
    <section className="dash-blank">
      <h1>Toilets in Sydney</h1>
      <p>The map of where Sydney needs public toilets will go here.</p>
    </section>
  )
}
