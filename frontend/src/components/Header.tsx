import { RefreshCw, TrendingUp } from 'lucide-react'
import { triggerRefresh } from '../hooks/useSpreadData'
import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

interface Props {
  lastUpdate: number | null
  isScanning: boolean
  cacheAge: number | null
}

export default function Header({ lastUpdate, isScanning, cacheAge }: Props) {
  const qc = useQueryClient()
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    await triggerRefresh()
    setTimeout(() => {
      qc.invalidateQueries({ queryKey: ['spreads'] })
      setRefreshing(false)
    }, 1500)
  }

  const formatTime = (ts: number | null) => {
    if (!ts) return '—'
    return new Date(ts * 1000).toLocaleTimeString()
  }

  const ageLabel = () => {
    if (isScanning) return 'Scanning…'
    if (cacheAge === null) return 'No data yet'
    if (cacheAge < 60) return `${cacheAge}s ago`
    return `${Math.floor(cacheAge / 60)}m ago`
  }

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-[#161b22] border-b border-[#30363d]">
      {/* Logo + title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-[#58a6ff]/20">
          <TrendingUp className="w-5 h-5 text-[#58a6ff]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">SpreadHunter</h1>
          <p className="text-xs text-gray-400">Bull Put Credit Spread Scanner</p>
        </div>
      </div>

      {/* Status + refresh */}
      <div className="flex items-center gap-4">
        <div className="text-right hidden sm:block">
          <p className="text-xs text-gray-400">Last scan</p>
          <p className="text-sm text-gray-200 font-medium">{formatTime(lastUpdate)}</p>
        </div>
        <div className="text-right hidden sm:block">
          <p className="text-xs text-gray-400">Data age</p>
          <p className={`text-sm font-medium ${isScanning ? 'text-yellow-400' : 'text-gray-200'}`}>
            {ageLabel()}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing || isScanning}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#58a6ff]/10 border border-[#58a6ff]/30 text-[#58a6ff] text-sm font-medium hover:bg-[#58a6ff]/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${(refreshing || isScanning) ? 'animate-spin' : ''}`} />
          {isScanning ? 'Scanning' : 'Refresh'}
        </button>
      </div>
    </header>
  )
}
