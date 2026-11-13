import { Show, SignInButton, UserButton } from '@clerk/tanstack-react-start'
import { Link, createFileRoute } from '@tanstack/react-router'
import { useEffect, useRef } from 'react'
import { HEX_DATA_URL, startLanding } from '../landing/engine'
import { clerkEnabled } from '../lib/clerk'
import '../landing/landing.css'

const TITLE = "Pigeon AI: where Sydney's next public infrastructure should go"
const DESCRIPTION =
  "Pigeon AI is a bird's-eye-view model that predicts where Sydney's next public infrastructure should go, starting with public toilets."

export const Route = createFileRoute('/')({
  head: () => ({
    meta: [{ title: TITLE }, { name: 'description', content: DESCRIPTION }],
    links: [
      { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
      { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossOrigin: 'anonymous' },
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:wght@400;700&family=Dela+Gothic+One&display=swap',
      },
      { rel: 'preload', href: HEX_DATA_URL, as: 'fetch', crossOrigin: 'anonymous' },
    ],
  }),
  component: Landing,
})

const PLANNED_SITES = 42
const PLANNED_IN_TOP_10 = 30

function Landing() {
  const rootRef = useRef<HTMLDivElement>(null)
  useEffect(() => (rootRef.current ? startLanding(rootRef.current) : undefined), [])

  return (
    <div className="landing-v3 intro" ref={rootRef}>
      <a className="skip" href="#main">
        Skip to content
      </a>

      <header className="nav">
        <a className="brand" href="#top" aria-label="Pigeon AI, back to top">
          <Logo />
          <Wordmark />
        </a>
        <div className="auth">
          <NavAuth />
        </div>
      </header>

      <section className="hero" id="top" aria-label="Sky over Sydney">
        <canvas className="sky" aria-hidden="true" />
        <div className="sign" aria-hidden="true">
          {(['y', 'p', 'b'] as const).map((ink) => (
            <span key={ink} className={`pass pass-${ink}`}>
              <span className="row">
                <i>PIGEON</i>
              </span>
              <span className="row">
                <i>AI</i>
              </span>
            </span>
          ))}
        </div>
        <canvas className="flock" aria-hidden="true" />
      </section>

      <main className="panel" id="main">
        <div className="top">
          <h1>A pigeon's-eye view of where Sydney's next public infrastructure should go.</h1>
          <p className="sub">
            The model scores the whole city, from established suburbs to growth areas still being planned. Public toilets are the
            first layer, with more to come.
          </p>
          <Link className="cta" to="/app">
            See the toilet layer
          </Link>
        </div>

        <section className="press" aria-label="How the model reads the map">
          <div className="stage">
            <div>
              <p className="layer">Layer shown: public toilets</p>
              <ol className="steps">
                <li>
                  The model looks down on Sydney as <b>16,228 hexagons</b>, each a few blocks wide.
                </li>
                <li>
                  It scores every hexagon for what's missing. <b>Bigger dot, bigger gap.</b>
                </li>
                <li>
                  <b>Pink dots</b> show what's already there: hexagons with a public toilet.
                </li>
                <li>
                  <b>Dark hexagons</b> are the model's <b>100 suggested spots</b>, where the gap is biggest. A few are circled.
                </li>
              </ol>
            </div>
            <div className="mapwrap">
              <canvas
                className="map"
                role="img"
                aria-label="Map of Sydney as hexagon dots, showing the public toilet layer. Larger blue dots show a bigger gap, pink dots show existing toilets, and 100 dark hexagons show where the model suggests new ones."
              />
              <svg className="marks" aria-hidden="true" />
            </div>
          </div>
        </section>

        <section className="proof" aria-label="Checking the model">
          <p>
            Councils already plan {PLANNED_SITES} new public toilet sites. {PLANNED_IN_TOP_10} of them land in the model's top 10%.
          </p>
          <div className="pips" role="img" aria-label={`${PLANNED_SITES} hexagons, ${PLANNED_IN_TOP_10} filled`}>
            {Array.from({ length: PLANNED_SITES }, (_, i) => (
              <Pip key={i} filled={i < PLANNED_IN_TOP_10} />
            ))}
          </div>
          <small>Each filled hexagon is a planned site the model ranks in its top 10%.</small>
        </section>

        <section className="ahead" aria-label="Where it goes next">
          <p>
            It also scores places it never trained on: fast-growing suburbs, and planned areas like the Aerotropolis at Bradfield and
            Leppington.
          </p>
          <p>Public toilets are the first infrastructure type. Others will follow.</p>
        </section>

        <footer>
          <Wordmark />
          <span className="blurb">Predicting where public infrastructure should go across Greater Sydney, starting with public toilets.</span>
          <FooterAuth />
        </footer>
      </main>

      <div className="grain" aria-hidden="true" />
    </div>
  )
}

function OpenApp() {
  return (
    <Link className="signin" to="/app">
      Open the app
    </Link>
  )
}

function SignIn() {
  return (
    <SignInButton>
      <button className="signin" type="button">
        Sign in
      </button>
    </SignInButton>
  )
}

function NavAuth() {
  if (!clerkEnabled) return <OpenApp />
  return (
    <>
      <Show when="signed-out">
        <SignIn />
      </Show>
      <Show when="signed-in">
        <OpenApp />
        <UserButton />
      </Show>
    </>
  )
}

function FooterAuth() {
  if (!clerkEnabled) return <OpenApp />
  return (
    <>
      <Show when="signed-out">
        <SignIn />
      </Show>
      <Show when="signed-in">
        <OpenApp />
      </Show>
    </>
  )
}

function Wordmark() {
  return (
    <span className="word">
      <span className="ink" data-c="PIGEON AI">
        PIGEON AI
      </span>
    </span>
  )
}

function Logo() {
  return (
    <svg viewBox="0 0 100 120" aria-hidden="true">
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

function Pip({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 22 25" aria-hidden="true">
      {filled ? (
        <>
          <path d="M11 1.5 20.5 7v11L11 23.5 1.5 18V7z" fill="#3255A4" />
          <path d="M12.2 2.5 21.5 8v11l-9.3 5.5z" fill="#FF48B0" style={{ mixBlendMode: 'multiply' }} opacity=".55" />
        </>
      ) : (
        <path d="M11 1.5 20.5 7v11L11 23.5 1.5 18V7z" fill="none" stroke="#3255A4" strokeWidth="2" />
      )}
    </svg>
  )
}
