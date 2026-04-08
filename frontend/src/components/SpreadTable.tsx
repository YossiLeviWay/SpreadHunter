import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import type { Spread } from '../types'

const col = createColumnHelper<Spread>()

// ── helpers ────────────────────────────────────────────────────────────────────
const usd = (v: number) => `$${v.toFixed(2)}`
const pct = (v: number) => `${v.toFixed(1)}%`

function rorBadge(v: number) {
  if (v >= 25) return 'text-[#3fb950] font-bold'
  if (v >= 15) return 'text-yellow-400 font-semibold'
  return 'text-gray-300'
}
function probBadge(v: number) {
  if (v <= 15) return 'text-[#3fb950] font-bold'
  if (v <= 25) return 'text-yellow-400 font-semibold'
  return 'text-[#f85149] font-semibold'
}
function distBadge(v: number) {
  if (v >= 10) return 'text-[#3fb950] font-bold'
  if (v >= 5)  return 'text-yellow-400 font-semibold'
  return 'text-[#f85149] font-semibold'
}

function categoryBadge(cat: string) {
  const styles: Record<string, string> = {
    'Sector ETF': 'bg-blue-500/20 text-blue-300',
    'Market ETF': 'bg-purple-500/20 text-purple-300',
    'Stock':      'bg-green-500/20 text-green-300',
  }
  return styles[cat] ?? 'bg-gray-500/20 text-gray-300'
}

// ── column definitions ─────────────────────────────────────────────────────────
const columns = [
  col.accessor('ticker', {
    header: 'Ticker',
    cell: info => (
      <div className="flex flex-col gap-0.5">
        <span className="font-bold text-white">{info.getValue()}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full w-fit ${categoryBadge(info.row.original.category)}`}>
          {info.row.original.category}
        </span>
      </div>
    ),
  }),

  col.accessor('short_strike', {
    header: 'Sell Put Strike',
    cell: info => (
      <div className="text-right">
        <div className="font-mono font-semibold text-white">${info.getValue()}</div>
        <div className="text-[10px] text-gray-400">@ {usd(info.row.original.short_put_premium)}</div>
      </div>
    ),
  }),

  col.accessor('long_strike', {
    header: 'Buy Put Strike',
    cell: info => (
      <div className="text-right">
        <div className="font-mono font-semibold text-white">${info.getValue()}</div>
        <div className="text-[10px] text-gray-400">@ {usd(info.row.original.long_put_premium)}</div>
      </div>
    ),
  }),

  col.accessor('dte', {
    header: 'DTE',
    cell: info => (
      <span className="font-mono text-gray-300">{info.getValue()}d</span>
    ),
  }),

  col.accessor('delta', {
    header: 'Delta',
    cell: info => (
      <span className="font-mono text-gray-300">{info.getValue().toFixed(3)}</span>
    ),
  }),

  col.accessor('prob_assignment', {
    header: 'Prob. Assignment',
    cell: info => (
      <div className="text-right">
        <span className={`font-mono ${probBadge(info.getValue())}`}>
          {pct(info.getValue())}
        </span>
      </div>
    ),
  }),

  col.accessor('net_credit', {
    header: 'Net Credit',
    cell: info => (
      <span className="font-mono font-semibold text-[#3fb950]">{usd(info.getValue())}</span>
    ),
  }),

  col.accessor('max_loss_per_contract', {
    header: 'Max Loss / Contract',
    cell: info => (
      <span className="font-mono text-[#f85149]">{usd(info.getValue())}</span>
    ),
  }),

  col.accessor('return_on_risk', {
    header: 'Return on Risk',
    cell: info => (
      <span className={`font-mono ${rorBadge(info.getValue())}`}>
        {pct(info.getValue())}
      </span>
    ),
  }),

  col.accessor('broken_nose_ratio', {
    header: () => (
      <span title="Net credit per 1% probability of assignment. Higher = more efficient.">
        Broken Nose Ratio ⓘ
      </span>
    ),
    cell: info => (
      <span className="font-mono text-purple-300">{info.getValue().toFixed(2)}</span>
    ),
  }),

  col.accessor('distance_from_danger', {
    header: 'Distance from Danger',
    cell: info => (
      <div className="text-right">
        <span className={`font-mono ${distBadge(info.getValue())}`}>
          {pct(info.getValue())}
        </span>
        <div className="text-[10px] text-gray-400 mt-0.5">
          ${info.row.original.current_price.toFixed(2)} → ${info.row.original.short_strike}
        </div>
      </div>
    ),
  }),

  col.accessor('total_profit', {
    header: 'Total Profit',
    cell: info => (
      <span className="font-mono font-bold text-[#3fb950]">{usd(info.getValue())}</span>
    ),
  }),
]

// ── component ─────────────────────────────────────────────────────────────────
interface Props {
  data: Spread[]
  isLoading: boolean
  error: Error | null
}

export default function SpreadTable({ data, isLoading, error }: Props) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'return_on_risk', desc: true },
  ])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-[#f85149]">
        <p>Error loading data: {error.message}</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto">
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 z-10 bg-[#161b22] border-b border-[#30363d]">
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              {hg.headers.map(header => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className={`
                    px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider
                    whitespace-nowrap select-none border-r border-[#30363d] last:border-r-0
                    ${header.column.getCanSort() ? 'cursor-pointer hover:text-white hover:bg-[#1f2937]' : ''}
                  `}
                >
                  <div className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getCanSort() && (
                      <span className="text-gray-600">
                        {header.column.getIsSorted() === 'asc'  ? <ChevronUp className="w-3 h-3" /> :
                         header.column.getIsSorted() === 'desc' ? <ChevronDown className="w-3 h-3" /> :
                         <ChevronsUpDown className="w-3 h-3" />}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          ))}
        </thead>

        <tbody>
          {isLoading && data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center py-16 text-gray-400">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-[#58a6ff] border-t-transparent rounded-full animate-spin" />
                  <p>Scanning option chains… This may take a minute on first load.</p>
                </div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center py-16 text-gray-400">
                No spreads match your current filters.
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row, i) => (
              <tr
                key={row.id}
                className={`
                  border-b border-[#30363d] transition-colors
                  ${i % 2 === 0 ? 'bg-[#0d1117]' : 'bg-[#161b22]/50'}
                  hover:bg-[#58a6ff]/5
                `}
              >
                {row.getVisibleCells().map(cell => (
                  <td
                    key={cell.id}
                    className="px-4 py-3 border-r border-[#30363d]/50 last:border-r-0"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* Row count footer */}
      {data.length > 0 && (
        <div className="px-4 py-2 text-xs text-gray-500 border-t border-[#30363d]">
          Showing {table.getRowModel().rows.length} of {data.length} spreads
        </div>
      )}
    </div>
  )
}
