export interface Spread {
  ticker: string
  category: string
  expiration: string
  dte: number
  current_price: number
  // Legs
  short_strike: number       // sell put strike
  long_strike: number        // buy put strike
  short_put_premium: number
  long_put_premium: number
  // Greeks
  delta: number
  prob_assignment: number    // %
  iv: number                 // %
  // P&L
  net_credit: number         // $
  max_loss_per_contract: number  // $
  return_on_risk: number     // %
  broken_nose_ratio: number
  distance_from_danger: number  // %
  total_profit: number       // $ per contract
}

export interface SpreadsResponse {
  spreads: Spread[]
  total: number
  is_scanning: boolean
  last_update: number | null
  cache_age_seconds: number | null
}

export interface Filters {
  min_ror: number
  max_prob: number
  min_credit: number
  min_distance: number
  category: string
  ticker: string
}
