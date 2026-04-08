import { Search, SlidersHorizontal } from 'lucide-react'
import type { Filters } from '../types'

interface Props {
  filters: Filters
  onChange: (f: Filters) => void
}

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs text-gray-400 mb-1">{children}</label>
}

function NumberInput({
  value, onChange, min, max, step, label,
}: {
  value: number; onChange: (v: number) => void
  min?: number; max?: number; step?: number; label: string
}) {
  return (
    <div>
      <Label>{label}</Label>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step ?? 1}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
        className="w-full bg-[#0d1117] border border-[#30363d] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#58a6ff]"
      />
    </div>
  )
}

export default function FilterPanel({ filters, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch })

  return (
    <div className="px-6 py-4 bg-[#161b22] border-b border-[#30363d]">
      <div className="flex items-center gap-2 mb-3">
        <SlidersHorizontal className="w-4 h-4 text-[#58a6ff]" />
        <span className="text-sm font-semibold text-white">Filters</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Ticker search */}
        <div>
          <Label>Ticker</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
            <input
              type="text"
              placeholder="NVDA…"
              value={filters.ticker}
              onChange={e => set({ ticker: e.target.value.toUpperCase() })}
              className="w-full pl-8 bg-[#0d1117] border border-[#30363d] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#58a6ff]"
            />
          </div>
        </div>

        {/* Category */}
        <div>
          <Label>Category</Label>
          <select
            value={filters.category}
            onChange={e => set({ category: e.target.value })}
            className="w-full bg-[#0d1117] border border-[#30363d] text-white text-sm rounded-md px-3 py-2 focus:outline-none focus:border-[#58a6ff]"
          >
            <option value="">All</option>
            <option value="sector_etfs">Sector ETFs</option>
            <option value="market_etfs">Market ETFs</option>
            <option value="top_stocks">Top Stocks</option>
          </select>
        </div>

        <NumberInput
          label="Min Return on Risk %"
          value={filters.min_ror}
          onChange={v => set({ min_ror: v })}
          min={0} max={100} step={1}
        />

        <NumberInput
          label="Max Prob. Assignment %"
          value={filters.max_prob}
          onChange={v => set({ max_prob: v })}
          min={0} max={100} step={1}
        />

        <NumberInput
          label="Min Net Credit $"
          value={filters.min_credit}
          onChange={v => set({ min_credit: v })}
          min={0} step={0.05}
        />

        <NumberInput
          label="Min Distance from Danger %"
          value={filters.min_distance}
          onChange={v => set({ min_distance: v })}
          min={0} step={0.5}
        />
      </div>
    </div>
  )
}
