import type { Ratio } from '../lib/data'

export const fmtRatio = (r: Ratio) => `${r.x.toLocaleString()}/${r.y.toLocaleString()} (${r.pct}%)`

interface BarItem {
  label: string
  value: number
  max: number
  text: string
  color?: string
}

/** Horizontal bars in plain SVG. Each bar's exact numbers are printed beside it. */
export function Bars({ items }: { items: BarItem[] }) {
  return (
    <div className="bars" role="list">
      {items.map((it) => (
        <div key={it.label} style={{ display: 'contents' }} role="listitem">
          <span>{it.label}</span>
          <svg viewBox="0 0 400 22" preserveAspectRatio="none" role="img" aria-label={`${it.label}: ${it.text}`}>
            <rect x="0" y="3" width="400" height="16" fill="#e8ecef" />
            <rect x="0" y="3" width={Math.max(0, Math.min(1, it.value / it.max)) * 400} height="16" fill={it.color ?? '#3d5a73'} />
          </svg>
          <span style={{ gridColumn: '2', fontSize: '0.8rem', color: 'var(--muted)', marginTop: '-0.3rem' }}>{it.text}</span>
        </div>
      ))}
    </div>
  )
}

export function Table({ head, rows, numFrom = 1 }: { head: string[]; rows: (string | number)[][]; numFrom?: number }) {
  return (
    <table className="t">
      <thead>
        <tr>
          {head.map((h, i) => (
            <th key={h} className={i >= numFrom ? 'num' : undefined}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((c, j) => (
              <td key={j} className={j >= numFrom ? 'num' : undefined}>
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
