/**
 * The landing page's canvas work: the halftone sky, the pigeons, the intro timeline and
 * the scroll-printed hex map. Call startLanding(root) after mount; it returns a cleanup
 * that stops every frame loop, listener, observer and timer, so the route can unmount
 * and mount again on client navigation.
 */

/** public/landing-hexes.json, built by scripts/build_landing_data.py */
export type HexData = {
  w: number
  h: number
  r: number
  /** "x,y,x,y,..." hex centres in map units */
  xy: string
  /** per hex: 'p' suggested spot, 't' has a toilet, '1'..'9' gap level, '0' no gap */
  s: string
  /** indices of the suggested spots, best first */
  picks: number[]
}

export const HEX_DATA_URL = '/landing-hexes.json'

const INK = { blue: '#3255A4', pink: '#FF48B0', yellow: '#FFE800', paper: '#FAFAF6' }
const clamp = (v: number, a = 0, b = 1) => (v < a ? a : v > b ? b : v)
const rand = (a: number, b: number) => a + Math.random() * (b - a)

type Plate = { ink: string; ang: number; t0: number; t1: number; mx: number; my: number }
type Cloud = { x: number; y: number; s: number; puffs: { dx: number; dy: number; r: number }[] }
type Bird = { x: number; y0: number; size: number; v: number; period: number; ph: number; wob: number; wf: number; delay: number }
type BirdOpts = Partial<Pick<Bird, 'x' | 'size' | 'v' | 'period' | 'wob' | 'delay'>> & { z?: number; y?: number }

function el<T extends Element>(root: Element, selector: string): T {
  const found = root.querySelector<T>(selector)
  if (!found) throw new Error(`landing: missing ${selector}`)
  return found
}

function ctx2d(c: HTMLCanvasElement): CanvasRenderingContext2D {
  const ctx = c.getContext('2d')
  if (!ctx) throw new Error('landing: no 2d canvas')
  return ctx
}

export function startLanding(root: HTMLElement): () => void {
  const ac = new AbortController()
  const { signal } = ac
  const on = <K extends keyof WindowEventMap>(type: K, fn: (e: WindowEventMap[K]) => void, opts: AddEventListenerOptions = {}) =>
    addEventListener(type, fn, { ...opts, signal })
  const timers = new Set<ReturnType<typeof setTimeout>>()
  const later = (fn: () => void, ms: number) => {
    const id = setTimeout(() => {
      timers.delete(id)
      fn()
    }, ms)
    timers.add(id)
  }
  let disposed = false

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
  const hero = el<HTMLElement>(root, '.hero')

  /* =================== SKY: three halftone plates, computed once per size =================== */
  const sky = el<HTMLCanvasElement>(root, '.sky')
  const sctx = ctx2d(sky)
  let W = 0
  let H = 0
  let DPR = 1
  let plates: (Plate & { c: HTMLCanvasElement })[] = []
  let clouds: Cloud[] = []
  const PLATES: Plate[] = [
    // each ink on its own screen angle, like a real riso run
    { ink: INK.yellow, ang: 5, t0: 0, t1: 330, mx: -1, my: 1 },
    { ink: INK.pink, ang: 75, t0: 90, t1: 430, mx: 1.6, my: -1.2 },
    { ink: INK.blue, ang: 15, t0: 180, t1: 530, mx: 0, my: 0 },
  ]
  function makeClouds() {
    const r = (s: number) => {
      const x = Math.sin(s * 999.7) * 43758.5453
      return x - Math.floor(x)
    }
    clouds = []
    const n = W < 700 ? 5 : 7
    for (let i = 0; i < n; i++) {
      const s = (W < 700 ? 0.7 : 1) * (0.75 + r(i + 1) * 0.7) * Math.min(W, H) * 0.11
      const puffs = []
      const k = 4 + Math.floor(r(i + 9) * 3)
      for (let j = 0; j < k; j++) {
        const t = j / (k - 1) - 0.5
        puffs.push({ dx: t * s * 3.2, dy: -Math.cos(t * Math.PI) * s * 0.55 + r(i * 7 + j) * s * 0.2, r: s * (0.75 + Math.cos(t * Math.PI) * 0.55) })
      }
      clouds.push({ x: r(i + 3) * W * 1.3 - W * 0.15, y: H * (0.12 + r(i + 5) * 0.5), s, puffs })
    }
  }
  function cloudAt(x: number, y: number) {
    let c = 0
    for (const cl of clouds) {
      if (Math.abs(x - cl.x) > cl.s * 3 || Math.abs(y - cl.y) > cl.s * 1.8) continue
      for (const p of cl.puffs) {
        const dx = x - (cl.x + p.dx)
        const dy = (y - (cl.y + p.dy)) * 1.25
        const d = Math.sqrt(dx * dx + dy * dy) / p.r
        if (d < 1) {
          const v = d < 0.55 ? 1 : 1 - (d - 0.55) / 0.45
          if (v > c) c = v
        }
      }
    }
    return c
  }
  function plateValue(i: number, x: number, y: number) {
    const yn = y / H
    const sunX = W * (W < 700 ? 0.72 : 0.8)
    const sunY = H * 0.6
    const sunR = Math.min(W, H) * 0.13
    const d = Math.hypot(x - sunX, y - sunY) / sunR
    const c = cloudAt(x, y)
    if (i === 0) {
      // yellow: sun + low warm haze
      const v = d < 0.85 ? 1 : d < 1.15 ? 1 - ((d - 0.85) / 0.3) * 0.5 : Math.max(0, 0.5 - (d - 1.15) * 0.6)
      return Math.max(v, 0.2 * yn * yn) * (1 - c * 0.6)
    }
    if (i === 1) {
      // pink: horizon glow + cloud undersides
      const under = Math.max(0, cloudAt(x, y - Math.min(W, H) * 0.035) - c)
      return Math.max(0.6 * Math.pow(yn, 2.4) + (d < 2.2 ? 0.25 * (1 - d / 2.2) : 0), under * 1.1) * (1 - c * 0.75) + c * 0.1
    }
    // blue: deep at the top, thinning to the horizon; clouds and the sun are bare paper
    const sun = d < 1.15 ? 1 : d < 1.7 ? 1 - (d - 1.15) / 0.55 : 0
    return (0.82 * Math.pow(1 - yn, 1.25) + 0.05) * (1 - c * 0.97) * (1 - sun)
  }
  // Each plate is screened once into its own bitmap. The intro composites those bitmaps;
  // afterwards the visible canvas is never redrawn.
  function screenPlates() {
    const cell = W < 700 ? 7.5 : 10
    const D = Math.hypot(W, H)
    plates = PLATES.map((p, i) => {
      const c = document.createElement('canvas')
      c.width = W * DPR
      c.height = H * DPR
      const ctx = ctx2d(c)
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0)
      const a = (p.ang * Math.PI) / 180
      const ca = Math.cos(a)
      const sa = Math.sin(a)
      const rmax = cell * 0.62
      ctx.fillStyle = p.ink
      ctx.beginPath()
      for (let u = -D; u < D; u += cell)
        for (let v = -D; v < D; v += cell) {
          const x = W / 2 + u * ca - v * sa
          const y = H / 2 + u * sa + v * ca
          if (x < -cell || x > W + cell || y < -cell || y > H + cell) continue
          const val = plateValue(i, x, y)
          if (val < 0.03) continue
          const r = rmax * Math.sqrt(val)
          ctx.moveTo(x + p.mx + r, y + p.my)
          ctx.arc(x + p.mx, y + p.my, r, 0, 6.2832)
        }
      ctx.fill()
      return { ...p, c }
    })
  }
  function sizeSky() {
    DPR = Math.min(2, devicePixelRatio || 1)
    W = sky.clientWidth
    H = sky.clientHeight
    sky.width = W * DPR
    sky.height = H * DPR
    makeClouds()
    screenPlates()
    sizeFlock()
  }
  // t = ms into the intro, or null for the finished print
  function drawSky(t: number | null) {
    sctx.setTransform(1, 0, 0, 1, 0, 0)
    sctx.globalCompositeOperation = 'source-over'
    sctx.fillStyle = INK.paper
    sctx.fillRect(0, 0, sky.width, sky.height)
    sctx.globalCompositeOperation = 'multiply'
    for (const p of plates) {
      const prog = t == null ? 1 : clamp((t - p.t0) / (p.t1 - p.t0))
      if (prog <= 0) continue
      const h = Math.ceil(sky.height * (1 - Math.pow(1 - prog, 2))) // the roller comes down fast and eases out
      sctx.drawImage(p.c, 0, 0, sky.width, h, 0, 0, sky.width, h)
    }
    sctx.globalCompositeOperation = 'source-over'
  }

  /* =================== PIGEONS: one canvas, pre-rendered sprites =================== */
  const flock = el<HTMLCanvasElement>(root, '.flock')
  const fctx = ctx2d(flock)
  const BIRD = new Path2D('M45 38 Q26 26 2 34 L8 40 L3 46 L10 50 L6 56 Q28 62 45 58 Z M55 38 Q74 26 98 34 L92 40 L97 46 L90 50 L94 56 Q72 62 55 58 Z')
  const BODY = new Path2D('M59 50 A9 20 0 1 1 41 50 A9 20 0 1 1 59 50 Z M57 27 A7 7 0 1 1 43 27 A7 7 0 1 1 57 27 Z M47.5 22 L50 15 L52.5 22 Z M44.5 66 L38 87 Q50 92 62 87 L55.5 66 Z')
  const NF = 10 // flap frames per cycle
  let sprites: HTMLCanvasElement[][] = [] // [tier][frame]; tier 0 = small, 1 = large
  function renderSprites() {
    sprites = [56, 132].map((px) =>
      Array.from({ length: NF }, (_, f) => {
        const s = Math.ceil(px * 1.12 * DPR)
        const c = document.createElement('canvas')
        c.width = c.height = s
        const ctx = ctx2d(c)
        const flap = 0.3 + 0.7 * Math.abs(Math.cos((Math.PI * f) / NF))
        const plate = (fill: string, dx: number, dy: number) => {
          ctx.save()
          ctx.translate(s / 2, s / 2)
          ctx.rotate(Math.PI / 2)
          ctx.scale((px * DPR) / 100, (px * DPR) / 100)
          ctx.translate(-50 + dx, -52 + dy)
          ctx.fillStyle = fill
          ctx.save()
          ctx.translate(50, 0)
          ctx.scale(flap, 1)
          ctx.translate(-50, 0)
          ctx.fill(BIRD)
          ctx.restore()
          ctx.fill(BODY)
          ctx.restore()
        }
        plate(INK.pink, 5, 4)
        plate(INK.yellow, 0, 0)
        return c
      }),
    )
  }
  function sizeFlock() {
    flock.width = W * DPR
    flock.height = H * DPR
    renderSprites()
  }

  let birds: Bird[] = []
  const small = () => W < 700
  // depth z: 0 = far (small, slow, high), 1 = near
  function addBird(o: BirdOpts) {
    const z = o.z ?? Math.random()
    const size = o.size ?? (small() ? 24 + z * 34 : 34 + z * 58)
    birds.push({
      x: o.x ?? -size - rand(0, 30),
      y0: o.y ?? H * rand(0.1, 0.5),
      size,
      v: o.v ?? (small() ? 55 + z * 110 : 70 + z * 170), // px per second
      period: o.period ?? rand(240, 380) * (1.2 - z * 0.4),
      ph: Math.random(),
      wob: o.wob ?? rand(4, 14),
      wf: rand(0.004, 0.009),
      delay: o.delay || 0,
    })
  }
  function spawnAmbient() {
    if (Math.random() < 0.24) {
      // a small group, flying together
      const n = 2 + Math.floor(Math.random() * 3)
      const z = rand(0.15, 0.8)
      const y = H * rand(0.12, 0.42)
      const v = small() ? 55 + z * 110 : 70 + z * 170
      for (let k = 0; k < n; k++) addBird({ z, y: y + rand(-1, 1) * H * 0.05, v: v * rand(0.96, 1.04), delay: k * rand(90, 200), x: -40 - k * rand(10, 30) })
    } else addBird({})
  }
  // the intro sweep: one tight flock, big and fast, right across the wordmark
  function addSweep() {
    const s = sign.getBoundingClientRect()
    const h = hero.getBoundingClientRect()
    const cy = s.top - h.top + s.height / 2
    const sz = small() ? 64 : 118
    const form = [[0, -0.2], [-1, -0.85], [-1.1, 0.55], [-2.1, -1.3], [-2.2, 1], [-3.1, -0.45], [-3.3, 0.9], [-4.2, -1], [-4.4, 0.2]] as const
    form.forEach(([fx, fy], k) =>
      addBird({ x: -sz + fx * sz * 1.25, y: cy + fy * s.height * 0.62, size: sz * (1 - k * 0.03), v: (W + sz * 6) / 1.2, period: rand(170, 220), wob: 6, delay: 120, z: 1 }),
    )
    // stragglers: slower birds that set off with the flock and are still crossing once it has gone
    ;([[0.2, 0.18], [0.55, 0.3], [0.8, 0.12], [0.4, 0.46]] as const).forEach(([z, y], k) =>
      addBird({ z, y: H * y, x: -60 - k * 90, v: (small() ? 120 : 190) + z * 120 }),
    )
  }
  let flyRaf = 0
  let flyLast = 0
  let nextSpawn = 0
  let flying = false
  let ambient = false
  let heroOn = true
  function drawBirds(now: number) {
    fctx.setTransform(1, 0, 0, 1, 0, 0)
    fctx.clearRect(0, 0, flock.width, flock.height)
    for (const b of birds) {
      if (b.delay > 0) continue
      const y = b.y0 + Math.sin(b.x * b.wf + b.ph * 6.28) * b.wob
      const f = Math.floor((((now / b.period + b.ph) % 1) * NF))
      const spr = sprites[b.size > 60 ? 1 : 0]?.[f]
      if (!spr) continue
      const d = b.size * 1.12 * DPR
      const tilt = Math.cos(b.x * b.wf + b.ph * 6.28) * 0.06
      fctx.setTransform(Math.cos(tilt), Math.sin(tilt), -Math.sin(tilt), Math.cos(tilt), b.x * DPR, y * DPR)
      fctx.drawImage(spr, -d / 2, -d / 2, d, d)
    }
  }
  function flyFrame(now: number) {
    const dt = Math.min(50, now - flyLast)
    flyLast = now
    for (const b of birds) {
      if (b.delay > 0) {
        b.delay -= dt
        continue
      }
      b.x += (b.v * dt) / 1000
    }
    birds = birds.filter((b) => b.x < W + b.size)
    if (ambient) {
      nextSpawn -= dt
      const live = birds.length
      const cap = small() ? 5 : 8
      if ((nextSpawn <= 0 && live < cap) || live < 2) {
        spawnAmbient()
        nextSpawn = rand(650, 2000)
      }
    }
    drawBirds(now)
    flyRaf = requestAnimationFrame(flyFrame)
  }
  // run only while the hero is on screen and the tab is visible
  function syncFlying() {
    const want = !disposed && !reduce && heroOn && document.visibilityState === 'visible' && (ambient || birds.length > 0)
    if (want && !flying) {
      flying = true
      flyLast = performance.now()
      flyRaf = requestAnimationFrame(flyFrame)
    } else if (!want && flying) {
      flying = false
      cancelAnimationFrame(flyRaf)
    }
  }
  const heroObserver = new IntersectionObserver((e) => {
    heroOn = e[e.length - 1]?.isIntersecting ?? heroOn
    syncFlying()
  })
  heroObserver.observe(hero)
  document.addEventListener('visibilitychange', syncFlying, { signal })
  function startAmbient() {
    ambient = true
    nextSpawn = 250
    syncFlying()
  }
  function staticBirds() {
    // reduced motion: a few birds, printed still
    birds = []
    ;([[0.14, 0.2, 0.55], [0.3, 0.12, 0.2], [0.55, 0.3, 0.75], [0.64, 0.24, 0.4], [0.69, 0.33, 0.35], [0.86, 0.14, 0.3]] as const).forEach(([x, y, z]) =>
      addBird({ x: W * x, y: H * y, z, wob: 0 }),
    )
    drawBirds(0)
  }

  /* =================== SIGN + FOLD =================== */
  const sign = el<HTMLElement>(root, '.sign')
  const navword = el<HTMLElement>(root, '.nav .word')
  let foldAnim: Animation | null = null
  function foldSign() {
    const a = sign.getBoundingClientRect()
    const b = navword.getBoundingClientRect()
    const firstRow = sign.querySelector('.row')
    const twoRows = firstRow ? getComputedStyle(firstRow).display === 'block' : false
    const s = (b.height / a.height) * (twoRows ? 2 : 1)
    const dx = b.left + b.width / 2 - (a.left + a.width / 2)
    const dy = b.top + b.height / 2 - (a.top + a.height / 2)
    const base = 'translate(-50%,-50%)'
    foldAnim = sign.animate(
      [
        { transform: `${base}`, opacity: 1 },
        { transform: `translate(${dx * 0.35}px,${dy * 0.3}px) ${base} perspective(900px) rotateX(-74deg) scale(${(1 + s) / 2.2})`, opacity: 1, offset: 0.42 },
        { transform: `translate(${dx * 0.86}px,${dy * 0.9}px) ${base} perspective(900px) rotateX(10deg) scale(${s * 1.12})`, opacity: 1, offset: 0.8 },
        { transform: `translate(${dx}px,${dy}px) ${base} scale(${s})`, opacity: 0 },
      ],
      { duration: 620, easing: 'cubic-bezier(.5,0,.2,1)', fill: 'forwards' },
    )
  }
  function cancelFold() {
    if (foldAnim) {
      foldAnim.cancel()
      foldAnim = null
    }
  }

  /* =================== INTRO TIMELINE (ms) =================== */
  const T = { sweep: 0, y: 380, p: 580, b: 780, skydone: 600, ambient: 1100, fold: 1450, rise: 1600, nav: 1950, end: 2450 }
  let introT = 0
  let introRaf = 0
  let introLast = 0
  let phase: 'idle' | 'intro' | 'settled' = 'idle'
  const fired = new Set<keyof typeof T>()
  function at(name: keyof typeof T, fn: () => void) {
    if (introT >= T[name] && !fired.has(name)) {
      fired.add(name)
      fn()
    }
  }
  function frameIntro(now: number) {
    introT += Math.min(50, now - introLast)
    introLast = now
    if (introT < T.skydone) drawSky(introT)
    else at('skydone', () => drawSky(null))
    at('sweep', () => {
      addSweep()
      syncFlying()
    })
    at('y', () => sign.classList.add('y'))
    at('p', () => sign.classList.add('p'))
    at('b', () => sign.classList.add('b'))
    at('ambient', startAmbient)
    at('fold', foldSign)
    at('rise', () => root.classList.add('rise'))
    at('nav', () => root.classList.add('navin'))
    if (introT >= T.end) {
      finishIntro()
      return
    }
    introRaf = requestAnimationFrame(frameIntro)
  }
  function finishIntro() {
    cancelAnimationFrame(introRaf)
    phase = 'settled'
    drawSky(null)
    cancelFold()
    sign.classList.remove('y', 'p', 'b')
    root.classList.add('rise', 'navin')
    root.classList.remove('intro')
    if (!ambient) startAmbient()
  }
  function startIntro() {
    if (reduce) {
      finishReduced()
      return
    }
    scrollTo(0, 0)
    root.classList.add('intro')
    root.classList.remove('rise', 'navin')
    sign.classList.remove('y', 'p', 'b')
    cancelFold()
    fired.clear()
    ambient = false
    birds = []
    drawBirds(0)
    phase = 'intro'
    introT = 0
    introLast = performance.now()
    drawSky(0)
    cancelAnimationFrame(introRaf)
    introRaf = requestAnimationFrame(frameIntro)
  }
  function finishReduced() {
    root.classList.remove('intro')
    phase = 'settled'
    drawSky(null)
    staticBirds()
  }
  // scrolling or a key skips the intro, once the wordmark has printed
  function trySkip(e: Event) {
    if (phase !== 'intro') return
    if (introT < T.b + 200) {
      if (e.cancelable && e.type !== 'keydown') e.preventDefault()
      return
    }
    finishIntro()
  }
  on('wheel', trySkip, { passive: false })
  on('touchmove', trySkip, { passive: false })
  on('keydown', (e) => {
    if (['ArrowDown', 'PageDown', ' ', 'End', 'Escape'].includes(e.key)) trySkip(e)
  })

  /* =================== MAP: four passes through the press =================== */
  const map = el<HTMLCanvasElement>(root, '.map')
  const mctx = ctx2d(map)
  const marks = el<SVGSVGElement>(root, '.marks')
  let hex: { xy: number[]; w: number; r: number; need: number[]; toilets: number[]; picks: number[]; zeros: number[]; level: Uint8Array; circled: number[] } | null = null
  function loadHex(d: HexData) {
    const xy = d.xy.split(',').map(Number)
    const need: number[] = []
    const toilets: number[] = []
    const zeros: number[] = []
    const level = new Uint8Array(d.s.length)
    for (let i = 0; i < d.s.length; i++) {
      const c = d.s[i]
      if (c === 'p') continue
      if (c === 't') toilets.push(i)
      else if (c === '0') zeros.push(i)
      else {
        need.push(i)
        level[i] = Number(c)
      }
    }
    const picks = d.picks
    // circle a few far-apart suggested spots (farthest-point picking from the top-ranked one)
    const circled = picks.slice(0, 1)
    while (circled.length < Math.min(5, picks.length)) {
      let best = -1
      let bd = -1
      for (const p of picks) {
        let dist = 1e18
        for (const q of circled) {
          const dx = xy[2 * p]! - xy[2 * q]!
          const dy = xy[2 * p + 1]! - xy[2 * q + 1]!
          dist = Math.min(dist, dx * dx + dy * dy)
        }
        if (dist > bd) {
          bd = dist
          best = p
        }
      }
      circled.push(best)
    }
    hex = { xy, w: d.w, r: d.r, need, toilets, picks, zeros, level, circled }
  }
  let MS = 1
  let mW = 0
  let mH = 0
  let mD = 1
  let mplates: HTMLCanvasElement[] = []
  let markEls: SVGPathElement[] = []
  function hexPath(ctx: CanvasRenderingContext2D, x: number, y: number, r: number) {
    for (let k = 0; k < 6; k++) {
      const a = (Math.PI / 3) * k + Math.PI / 6
      const px = x + r * Math.cos(a)
      const py = y + r * Math.sin(a)
      if (k) ctx.lineTo(px, py)
      else ctx.moveTo(px, py)
    }
    ctx.closePath()
  }
  // Screen each pass once into its own bitmap; scrolling only composites them.
  function screenMap() {
    if (!hex) return
    const { xy, need, toilets, picks, zeros, level } = hex
    const r = hex.r * MS
    const plate = (draw: (ctx: CanvasRenderingContext2D) => void) => {
      const c = document.createElement('canvas')
      c.width = map.width
      c.height = map.height
      const ctx = ctx2d(c)
      ctx.setTransform(mD, 0, 0, mD, 0, 0)
      draw(ctx)
      return c
    }
    const dots = (ctx: CanvasRenderingContext2D, ids: number[], fill: string, rad: (i: number) => number) => {
      ctx.fillStyle = fill
      ctx.beginPath()
      for (const i of ids) {
        const x = xy[2 * i]! * MS
        const y = xy[2 * i + 1]! * MS
        const rr = rad(i)
        ctx.moveTo(x + rr, y)
        ctx.arc(x, y, rr, 0, 6.2832)
      }
      ctx.fill()
    }
    mplates = [
      // 1: every hexagon, a fine screen
      plate((ctx) => {
        dots(ctx, zeros, 'rgba(50,85,164,.38)', () => r * 0.3)
        dots(ctx, need, INK.blue, () => r * 0.3)
        dots(ctx, toilets, INK.pink, () => r * 0.3)
      }),
      // 2: the gap; dot size = how much is missing
      plate((ctx) => dots(ctx, need, INK.blue, (i) => r * (0.5 + 0.075 * level[i]!))),
      // 3: what's already there
      plate((ctx) => dots(ctx, toilets, INK.pink, () => r * 0.62)),
      // 4: where it should go, pink and blue overprinted
      plate((ctx) => {
        ctx.globalCompositeOperation = 'multiply'
        for (const [ink, off] of [[INK.pink, 0.9], [INK.blue, 0]] as const) {
          ctx.fillStyle = ink
          ctx.beginPath()
          for (const i of picks) hexPath(ctx, xy[2 * i]! * MS + off, xy[2 * i + 1]! * MS - off * 0.6, r * 1.25)
          ctx.fill()
        }
      }),
    ]
  }
  function sizeMap() {
    if (!hex) return
    const { xy, w, circled } = hex
    const b = map.getBoundingClientRect()
    mW = b.width
    mH = b.height
    mD = Math.min(2, devicePixelRatio || 1)
    map.width = Math.round(mW * mD)
    map.height = Math.round(mH * mD)
    MS = mW / w
    marks.setAttribute('viewBox', `0 0 ${mW} ${mH}`)
    marks.innerHTML = circled
      .map((i, n) => {
        const cx = xy[2 * i]! * MS
        const cy = xy[2 * i + 1]! * MS
        const R = Math.max(11, mW * 0.024)
        let d = ''
        for (let a = 0; a <= 1.12; a += 0.02) {
          const th = -2.2 + a * Math.PI * 2
          const wv = 1 + 0.12 * Math.sin(a * 9 + n) + a * 0.08
          d += (a ? 'L' : 'M') + (cx + Math.cos(th) * R * wv * 1.15).toFixed(1) + ' ' + (cy + Math.sin(th) * R * wv * 0.9).toFixed(1)
        }
        return `<path d="${d}" pathLength="1" stroke-dasharray="1 1" stroke-dashoffset="1"/>`
      })
      .join('')
    markEls = [...marks.querySelectorAll('path')]
    screenMap()
  }
  const pass = (p: number, a: number, b: number) => clamp((p - a) / (b - a))
  const PASSES = [[0, 0.2, 'source-over'], [0.22, 0.45, 'source-over'], [0.48, 0.66, 'source-over'], [0.7, 0.86, 'multiply']] as const
  function drawMap(p: number) {
    const ctx = mctx
    const w = map.width
    const h = map.height
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.globalCompositeOperation = 'source-over'
    ctx.clearRect(0, 0, w, h)
    PASSES.forEach(([a, b, op], k) => {
      const lp = pass(p, a, b)
      const plate = mplates[k]
      if (lp <= 0 || !plate) return
      const rows = Math.ceil(h * (1 - Math.pow(1 - lp, 2))) // the roller runs top to bottom
      ctx.globalCompositeOperation = op
      ctx.drawImage(plate, 0, 0, w, rows, 0, 0, w, rows)
    })
    ctx.globalCompositeOperation = 'source-over'
    const lp5 = pass(p, 0.86, 0.98)
    markEls.forEach((m, n) => m.setAttribute('stroke-dashoffset', String(1 - clamp(lp5 * 1.6 - n * 0.15))))
  }
  const steps = [...root.querySelectorAll<HTMLLIElement>('.steps li')]
  const press = el<HTMLElement>(root, '.press')
  let pressP = -1
  let stepIdx = -1
  function updatePress() {
    let p = 1
    if (!reduce) {
      const r = press.getBoundingClientRect()
      if (r.bottom < 0 || r.top > innerHeight) return // offscreen: nothing to print
      p = clamp((-r.top + innerHeight * 0.15) / (r.height - innerHeight * 0.9))
    }
    const idx = reduce ? 3 : p < 0.21 ? 0 : p < 0.47 ? 1 : p < 0.69 ? 2 : 3
    if (idx !== stepIdx) {
      stepIdx = idx
      steps.forEach((li, n) => li.classList.toggle('on', reduce || n === idx))
    }
    if (!hex || Math.abs(p - pressP) < 0.002) return
    pressP = p
    drawMap(p)
  }
  function redrawMap() {
    sizeMap()
    pressP = -1
    updatePress()
  }

  /* =================== WIRING =================== */
  const nav = el<HTMLElement>(root, '.nav')
  let scrollQueued = false
  let scrollRaf = 0
  let solid = false
  function onScrollFrame() {
    scrollQueued = false
    const s = scrollY > innerHeight * 0.45
    if (s !== solid) {
      solid = s
      nav.classList.toggle('solid', s)
    }
    updatePress()
  }
  on(
    'scroll',
    () => {
      if (!scrollQueued) {
        scrollQueued = true
        scrollRaf = requestAnimationFrame(onScrollFrame)
      }
    },
    { passive: true },
  )
  let rz: ReturnType<typeof setTimeout> | undefined
  let lastW = innerWidth
  on('resize', () => {
    clearTimeout(rz)
    rz = setTimeout(() => {
      const widthChanged = innerWidth !== lastW
      lastW = innerWidth
      if (!widthChanged && Math.abs(sky.clientHeight - H) < 120) return // mobile URL-bar jiggle: keep the print
      sizeSky()
      redrawMap()
      if (phase !== 'intro') drawSky(null)
      if (reduce) staticBirds()
      else birds = birds.filter((b) => b.y0 < H)
    }, 150)
  })
  el<HTMLButtonElement>(root, '.replay').addEventListener('click', startIntro, { signal })

  // the map data comes from public/, so the JS bundle stays small
  fetch(HEX_DATA_URL, { signal })
    .then((r) => {
      if (!r.ok) throw new Error(`landing: ${HEX_DATA_URL} ${r.status}`)
      return r.json() as Promise<HexData>
    })
    .then((d) => {
      if (disposed) return
      loadHex(d)
      redrawMap()
    })
    .catch((e: unknown) => {
      if (!disposed) console.error(e)
    })

  // the intro only starts when the tab is visible and fonts are in
  sizeSky()
  updatePress()
  drawSky(reduce ? null : 0)
  const fontsIn = Promise.race([
    Promise.all([document.fonts.load('40px "Dela Gothic One"'), document.fonts.load('18px "Atkinson Hyperlegible Next"')]).then(() => document.fonts.ready),
    new Promise<void>((r) => later(r, 3000)),
  ])
  const visible = () =>
    new Promise<void>((r) => {
      if (document.visibilityState === 'visible') return r()
      const h = () => {
        if (document.visibilityState === 'visible') {
          document.removeEventListener('visibilitychange', h)
          r()
        }
      }
      document.addEventListener('visibilitychange', h, { signal })
    })
  let startRaf = 0
  if (reduce) {
    finishReduced()
    void fontsIn.then(() => {
      if (!disposed) redrawMap()
    })
  } else {
    void fontsIn.then(visible).then(() => {
      if (disposed) return
      startRaf = requestAnimationFrame(() => {
        redrawMap()
        startIntro()
      })
    })
  }

  return () => {
    disposed = true
    ac.abort()
    heroObserver.disconnect()
    cancelAnimationFrame(introRaf)
    cancelAnimationFrame(flyRaf)
    cancelAnimationFrame(scrollRaf)
    cancelAnimationFrame(startRaf)
    clearTimeout(rz)
    timers.forEach(clearTimeout)
    timers.clear()
    cancelFold()
    flying = false
  }
}
