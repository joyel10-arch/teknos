import { Users } from 'lucide-react'
import { useData } from '../context/DataContext'
import { useMemo } from 'react'

export default function ActivityPanel() {
  const { tracks, zones } = useData()

  // Build tracks mapping
  const activeTracks = useMemo(() => {
    return (tracks || []).filter(t => t.is_valid_track).map(t => ({
      id: t.track_id,
      trackId: `#TRK-${t.track_id}`,
      label: t.entity_id,
      behaviour: t.behaviour || 'Monitored',
      status: t.status || 'Normal',
      speed: `${Math.abs(t.net_dx / (t.duration_seconds || 1)).toFixed(1)} px/s`,
      dwell: t.dwell || `${t.duration_seconds?.toFixed(1) || 0}s`,
      zone: 'Global',
    }))
  }, [tracks])

  // Build zones matrix
  const matrixZones = useMemo(() => {
    const zoneList = zones?.zones || []
    if (zoneList.length === 0) {
      return [
        { zone: 'AISLE 3', count: '0', danger: false },
        { zone: 'LOADING', count: '0', danger: false },
        { zone: 'BAY 4', count: '0', danger: false },
        { zone: 'GATE A', count: '0', danger: false }
      ]
    }
    return zoneList.slice(0, 4).map((z) => ({
      zone: z.name.toUpperCase().substring(0, 8),
      count: '-',
      danger: z.type === 'restricted'
    }))
  }, [zones])

  return (
    <div className="bg-surface-container-low rounded-lg p-4 shadow-sm flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-secondary" />
          <span className="text-[15px] font-semibold text-on-surface">Active Tracked Subjects</span>
        </div>
        <span className="px-1.5 py-0.5 rounded bg-surface-container-highest text-secondary font-mono text-[11px] font-semibold">
          {activeTracks.length} IN FRAME
        </span>
      </div>

      {/* Subjects list */}
      <div className="flex flex-col gap-1.5">
        {activeTracks.map((person) => {
          const isAbnormal = person.status === 'Abnormal'
          return (
            <div
              key={person.id}
              className={`p-2.5 rounded transition-colors flex flex-col gap-1 cursor-pointer ${
                isAbnormal
                  ? 'bg-error-container/20 hover:bg-error-container/30 shadow-inner'
                  : 'bg-surface-container hover:bg-surface-container-high'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${isAbnormal ? 'bg-error animate-ping' : 'bg-secondary'}`} />
                  <span className={`text-[15px] font-semibold ${isAbnormal ? 'text-error' : 'text-on-surface'}`}>
                    {person.label}
                  </span>
                  <span className="font-mono text-[11px] text-outline">{person.trackId}</span>
                </div>
                <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-bold ${
                  isAbnormal ? 'text-on-error bg-error' : 'text-tertiary bg-surface-container-highest'
                }`}>
                  {person.status.toUpperCase()}
                </span>
              </div>
              <div className="flex items-center justify-between text-on-surface-variant font-mono text-[11px] tracking-wider">
                <span>ACTION: <strong className={isAbnormal ? 'text-error font-bold' : 'text-on-surface'}>{person.behaviour}</strong></span>
                <span>DWELL: <strong className={isAbnormal ? 'text-error font-bold' : 'text-on-surface'}>{person.dwell}</strong></span>
                <span>SPEED: <strong className="text-secondary">{person.speed}</strong></span>
                <span>ZONE: <strong className={isAbnormal ? 'text-error font-bold' : 'text-outline'}>{person.zone}</strong></span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Zone occupancy matrix */}
      <div className="pt-1 flex flex-col gap-1.5">
        <div className="flex items-center justify-between font-mono text-[11px] text-outline tracking-wider">
          <span>ZONE OCCUPANCY RISK DENSITY</span>
          <span>MAX CAP: 8 PERS</span>
        </div>
        <div className="w-full grid grid-cols-4 gap-1">
          {matrixZones.map((z, idx) => (
            <div key={idx} className={`p-1 rounded flex flex-col items-center ${z.danger ? 'bg-error-container/40' : 'bg-surface-container'}`}>
              <span className={`font-mono text-[9px] ${z.danger ? 'text-error font-bold' : 'text-outline'}`}>{z.zone}</span>
              <span className={`font-mono text-[11px] ${z.danger ? 'text-error font-bold' : 'text-on-surface'}`}>{z.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
