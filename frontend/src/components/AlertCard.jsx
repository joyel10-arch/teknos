import { Shield, Play, AlertTriangle } from 'lucide-react'

export default function AlertCard({ alert }) {
  return (
    <div className="w-full bg-error-container/30 rounded-lg p-4 shadow-xl flex flex-col gap-3 relative overflow-hidden">
      {/* Ambient glow */}
      <div className="absolute -right-12 -top-12 w-40 h-40 bg-error/10 rounded-full blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-error animate-ping" />
          <span className="text-[15px] font-semibold text-on-error-container uppercase tracking-wide">Critical Anomaly Identified</span>
        </div>
        <span className="px-1.5 py-0.5 rounded bg-error text-on-error font-mono text-[11px] font-bold tracking-wider">
          THREAT ACTIVE
        </span>
      </div>

      {/* Title */}
      <div className="flex flex-col">
        <h3 className="text-[18px] font-bold text-on-surface leading-tight capitalize">{alert.eventType ? alert.eventType.replace(/_/g, ' ') : 'Unknown Event'}</h3>
        <span className="text-[12px] text-on-surface-variant mt-0.5">{alert.title || `Subject identified in ${alert.zoneName || 'zone'}`}</span>
      </div>

      {/* Data matrix */}
      <div className="grid grid-cols-2 gap-1.5 bg-surface-container-lowest/80 p-2.5 rounded-lg backdrop-blur">
        <div className="flex flex-col p-1.5">
          <span className="font-mono text-[11px] text-outline uppercase tracking-wider">WHO (TARGET)</span>
          <span className="font-mono text-[14px] text-error font-bold mt-0.5">{alert.personLabel}</span>
          <span className="font-mono text-[10px] text-on-surface-variant">#TRK-{alert.trackId}</span>
        </div>
        <div className="flex flex-col p-1.5">
          <span className="font-mono text-[11px] text-outline uppercase tracking-wider">WHEN (TIMECODE)</span>
          <span className="font-mono text-[14px] text-on-surface font-semibold mt-0.5">{alert.timestamp}</span>
          <span className="font-mono text-[10px] text-secondary">Recent</span>
        </div>
        <div className="flex flex-col p-1.5 col-span-2">
          <span className="font-mono text-[11px] text-outline uppercase tracking-wider">WHAT (CLASSIFICATION)</span>
          <span className="text-[13px] text-on-surface font-medium mt-0.5">{alert.title}</span>
        </div>
        <div className="flex flex-col p-1.5">
          <span className="font-mono text-[11px] text-outline uppercase tracking-wider">DURATION</span>
          <span className="font-mono text-[14px] text-error font-bold mt-0.5">{alert.dwell}</span>
          <span className="font-mono text-[10px] text-outline">Zone: {alert.zoneName}</span>
        </div>
        <div className="flex flex-col p-1.5">
          <span className="font-mono text-[11px] text-outline uppercase tracking-wider">AI CERTAINTY</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="font-mono text-[14px] text-error font-bold">{alert.anomalyScore?.toFixed(1) || 99}%</span>
            <AlertTriangle className="w-4 h-4 text-error" />
          </div>
          <span className="font-mono text-[10px] text-on-surface-variant">Temporal CNN v2</span>
        </div>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <button className="w-full py-2 bg-surface-container hover:bg-surface-container-high text-on-surface text-[15px] font-semibold rounded flex items-center justify-center gap-1.5 transition-colors shadow-sm">
          <Play className="w-[18px] h-[18px]" />
          View Event Clip
        </button>
        <button className="w-full py-2 bg-error hover:bg-on-error-container text-on-error text-[15px] font-semibold rounded flex items-center justify-center gap-1.5 transition-all shadow-md hover:shadow-[0_0_12px_rgba(255,180,171,0.5)]">
          <Shield className="w-[18px] h-[18px]" />
          Dispatch Security
        </button>
      </div>
    </div>
  )
}
