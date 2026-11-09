/** Clerk is optional: without a publishable key the app renders with sign-in disabled. */
export const clerkEnabled = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)
