import { useData } from '../context/DataContext'

export default function EventTimeline({ filter = 'All' }) {
  const { events, summary } = useData()
  
  const allEvents = events || []
  
  // Apply severity filter
  const displayEvents = filter === 'All' ? allEvents : allEvents.filter(e => {
    if (filter === 'Critical') return e.severity === 'high'
    if (filter === 'Warning') return e.severity === 'medium'
    if (filter === 'Normal') return e.severity === 'info' || e.severity === 'low'
    return true
  })

  // helper to format seconds to mm:ss
  const formatTime = (secs) => {
    if (secs == null) return '--:--'
    const m = Math.floor(secs / 60).toString().padStart(2, '0')
    const s = Math.floor(secs % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  return (
    <div className="bg-surface-container-lowest rounded-xl shadow-lg overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 bg-surface-container flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[15px] font-semibold text-on-surface">Temporal Audit Ledger</span>
          <span className="font-mono text-[11px] text-outline tracking-wider">
            VIDEO: {summary?.video_filename || 'Loading...'}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-secondary animate-ping" />
          <span className="font-mono text-[11px] text-secondary uppercase tracking-wider">Ingesting Buffer</span>
        </div>
      </div>

      {/* Table */}
      <div className="w-full overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-low text-outline font-mono text-[11px] uppercase tracking-wider">
              <th className="py-2 px-3">Time Index</th>
              <th className="py-2 px-3">Video / Zone</th>
              <th className="py-2 px-3">Tracked Entity</th>
              <th className="py-2 px-3">Detected Behaviour</th>
              <th className="py-2 px-3">Dwell</th>
              <th className="py-2 px-3">Classification</th>
              <th className="py-2 px-3">AI Conf</th>
            </tr>
          </thead>
          <tbody className="text-on-surface text-[12px]">
            {displayEvents.map((event, idx) => {
              const isAbnormal = event.severity === 'high'
              return (
                <tr
                  key={event.event_id}
                  className={`transition-colors cursor-pointer group ${
                    isAbnormal && idx === 0
                      ? 'bg-surface-container-high shadow-inner'
                      : 'hover:bg-surface-container-low'
                  }`}
                >
                  <td className="py-3 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-1 h-8 rounded-full ${isAbnormal ? 'bg-error' : 'bg-tertiary opacity-40 group-hover:opacity-100'}`} />
                      <div className="flex flex-col">
                        <span className="font-mono text-[14px] text-on-surface font-semibold">
                          {formatTime(event.start_time_seconds)}
                        </span>
                        <span className="font-mono text-[11px] text-outline">
                          {event.start_time_seconds?.toFixed(1)}s
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-on-surface">{event.zone_id || 'uploaded'}</span>
                      <span className={`font-mono text-[11px] ${isAbnormal ? 'text-error' : 'text-outline'}`}>{event.zone_name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-6 h-6 rounded flex items-center justify-center font-mono text-[11px] font-bold ${
                        isAbnormal ? 'bg-surface-container-highest text-error' : 'bg-surface-container-high text-on-surface-variant'
                      }`}>#{event.track_id}</div>
                      <div className="flex flex-col">
                        <span className="text-on-surface">{event.entity_id}</span>
                        <span className="font-mono text-[11px] text-outline">TRK-{event.track_id}</span>
                      </div>
                    </div>
                  </td>
                  <td className={`py-3 px-3 whitespace-nowrap max-w-xs truncate ${isAbnormal ? 'text-error font-medium' : 'text-on-surface-variant'}`} title={event.reason}>
                    {event.event_type.replace(/_/g, ' ')}
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap font-mono text-[14px] text-on-surface-variant">
                    {event.duration_seconds ? `${event.duration_seconds.toFixed(1)}s` : '-'}
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-mono text-[11px] font-bold ${
                      isAbnormal
                        ? 'bg-error-container text-on-error-container'
                        : 'bg-tertiary-container text-on-tertiary-container'
                    }`}>
                      {isAbnormal && <span className="w-1.5 h-1.5 rounded-full bg-error animate-ping" />}
                      {event.severity.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-3 whitespace-nowrap font-mono text-[14px] text-on-surface-variant">
                    {(event.confidence * 100).toFixed(1)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-4 py-2 bg-surface-container-low flex items-center justify-between mt-auto">
        <div className="font-mono text-[11px] text-outline tracking-wider">
          SHOWING {displayEvents.length} OF {allEvents.length} EVENTS
        </div>
      </div>
    </div>
  )
}
