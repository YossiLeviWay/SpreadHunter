import { useState } from 'react'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import FilterPanel from './components/FilterPanel'
import SpreadTable from './components/SpreadTable'
import { useSpreadData } from './hooks/useSpreadData'
import type { Filters } from './types'

const DEFAULT_FILTERS: Filters = {
  min_ror: 10,
  max_prob: 35,
  min_credit: 0.10,
  min_distance: 2,
  category: '',
  ticker: '',
}

export default function App() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const { data, isLoading, error } = useSpreadData(filters)

  const spreads = data?.spreads ?? []

  return (
    <div className="flex flex-col h-screen bg-[#0d1117] text-white overflow-hidden">
      <Header
        lastUpdate={data?.last_update ?? null}
        isScanning={data?.is_scanning ?? false}
        cacheAge={data?.cache_age_seconds ?? null}
      />
      <StatsBar spreads={spreads} total={data?.total ?? 0} />
      <FilterPanel filters={filters} onChange={setFilters} />

      <SpreadTable
        data={spreads}
        isLoading={isLoading}
        error={error as Error | null}
      />
    </div>
  )
}
