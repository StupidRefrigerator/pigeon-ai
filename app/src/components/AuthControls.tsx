import { Show, SignInButton, SignOutButton, UserButton } from '@clerk/tanstack-react-start'
import { clerkEnabled } from '../lib/clerk'

export function AuthControls() {
  if (!clerkEnabled) {
    return (
      <div className="actions" style={{ flexDirection: 'column' }}>
        <button className="btn" disabled>
          Sign in
        </button>
        <p className="note">Sign-in is not configured. Set VITE_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY.</p>
      </div>
    )
  }
  return (
    <div className="actions">
      <Show when="signed-out">
        <SignInButton forceRedirectUrl="/app" signUpForceRedirectUrl="/app">
          <button className="btn">Sign in</button>
        </SignInButton>
      </Show>
      <Show when="signed-in">
        <UserButton />
        <SignOutButton>
          <button className="btn">Sign out</button>
        </SignOutButton>
      </Show>
    </div>
  )
}
