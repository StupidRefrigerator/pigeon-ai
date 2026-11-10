import { clerkMiddleware } from '@clerk/tanstack-react-start/server'
import { createCsrfMiddleware, createStart } from '@tanstack/react-start'

const csrfMiddleware = createCsrfMiddleware({
  filter: (ctx) => ctx.handlerType === 'serverFn',
})

// Clerk only runs when keys are configured, so the app builds and renders without them.
const clerkConfigured = Boolean(process.env.CLERK_SECRET_KEY && process.env.VITE_CLERK_PUBLISHABLE_KEY)

export const startInstance = createStart(() => ({
  requestMiddleware: clerkConfigured ? [csrfMiddleware, clerkMiddleware()] : [csrfMiddleware],
}))
