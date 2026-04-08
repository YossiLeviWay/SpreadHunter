import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import type { Filters, SpreadsResponse } from '../types'

const API_BASE = '/api'

export function useSpreadData(filters: Filters) {
  return useQuery<SpreadsResponse>({
    queryKey: ['spreads', filters],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        min_ror: filters.min_ror,
        max_prob: filters.max_prob,
        min_credit: filters.min_credit,
        min_distance: filters.min_distance,
      }
      if (filters.category) params.category = filters.category
      if (filters.ticker)   params.ticker   = filters.ticker.toUpperCase()

      const { data } = await axios.get<SpreadsResponse>(`${API_BASE}/spreads`, { params })
      return data
    },
    refetchInterval: 30_000,   // auto-refresh every 30 s
    staleTime: 20_000,
    retry: 2,
  })
}

export async function triggerRefresh() {
  await axios.post(`${API_BASE}/refresh`)
}
