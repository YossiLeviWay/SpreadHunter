import type { Spread } from '../types'

interface Props {
  spreads: Spread[]
  total: number
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col items-center px-5 py-3 bg-[#161b22] rounded-lg border border-[#30363d]">
      <span className={`text-lg font-bold ${color ?? 'text-white'}`}>{value}</span>
      <span className="text-xs text-gray-400 mt-0.5 whitespace-nowrap">{label}</span>
    </div>
  )
}

export default function StatsBar({ spreads, total }: Props) {
  const best = spreads[0]
  const avgRor = spreads.length
    ? (spreads.reduce((s, x) => s + x.return_on_risk, 0) / spreads.length).toFixed(1)
    : '—'
  const avgProb = spreads.length
    ? (spreads.reduce((s, x) => s + x.prob_assignment, 0) / spreads.length).toFixed(1)
    : '—'
  const topBnr = spreads.length
    ? Math.max(...spreads.map(s => s.broken_nose_ratio)).toFixed(2)
    : '—'

  return (
    <div className="flex flex-wrap gap-3 px-6 py-4">
      <Stat label="Opportunities" value={String(total)} color="text-[#58a6ff]" />
      <Stat
        label="Best ROR"
        value={best ? `${best.return_on_risk.toFixed(1)}%` : '—'}
        color="text-[#3fb950]"
      />
      <Stat
        label="Avg ROR"
        value={spreads.length ? `${avgRor}%` : '—'}
        color="text-[#3fb950]"
      />
      <Stat
        label="Avg Prob. Assign."
        value={spreads.length ? `${avgProb}%` : '—'}
        color={parseFloat(avgProb) > 25 ? 'text-[#f85149]' : 'text-yellow-400'}
      />
      <Stat
        label="Top Broken Nose"
        value={topBnr !== '—' ? String(topBnr) : '—'}
        color="text-purple-400"
      />
      {best && (
        <Stat
          label="Best Trade"
          value={`${best.ticker} $${best.short_strike}/$${best.long_strike}`}
          color="text-[#58a6ff]"
        />
      )}
    </div>
  )
}
