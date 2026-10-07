import { TrendingUp } from 'lucide-react'

export default function StatCard({ label, value, icon: Icon, trend, trendLabel, description, detail, accentColor = 'primary', badge }) {
  const colorMap = {
    primary: { text: 'text-primary', bg: 'bg-primary/5', icon: 'text-primary' },
    secondary: { text: 'text-secondary', bg: 'bg-secondary/5', icon: 'text-secondary' },
    tertiary: { text: 'text-tertiary', bg: 'bg-tertiary/5', icon: 'text-tertiary' },
    error: { text: 'text-error', bg: 'bg-error/10', icon: 'text-error' },
  }
  const colors = colorMap[accentColor] || colorMap.primary

  return (
    <div className="group relative p-4 rounded-xl bg-surface-container-low hover:bg-surface-container transition-all duration-300 shadow-sm flex flex-col justify-between overflow-hidden">
      {/* Ambient glow */}
      <div className={`absolute -right-8 -bottom-8 w-28 h-28 ${colors.bg} rounded-full blur-xl group-hover:scale-125 transition-transform duration-500 pointer-events-none`} />

      <div>
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <span className="font-mono text-[11px] text-on-surface-variant uppercase tracking-wider">{label}</span>
          {Icon && <Icon className={`w-5 h-5 ${colors.icon}`} />}
        </div>

        {/* Value + trend */}
        <div className="flex items-baseline gap-2 mb-1">
          <span className={`text-[32px] font-bold tracking-tight leading-none ${accentColor === 'primary' ? 'text-on-surface' : colors.text}`}>
            {typeof value === 'number' ? value.toLocaleString() : value}
          </span>
          {trend && (
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-tertiary-container/30 text-tertiary font-mono text-[11px] font-semibold">
              <TrendingUp className="w-3 h-3" />
              {trend}
            </span>
          )}
          {badge && (
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-mono text-[11px] font-semibold ${
              accentColor === 'error' ? 'bg-error-container text-error' :
              accentColor === 'secondary' ? 'bg-secondary-container/20 text-secondary' :
              'bg-tertiary-container/30 text-tertiary'
            }`}>
              {accentColor === 'secondary' && <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-ping" />}
              {badge}
            </span>
          )}
        </div>
        <p className="text-[12px] text-on-surface-variant">{description}</p>
      </div>

      {/* Footer */}
      <div className="mt-3 pt-2 flex items-center justify-between text-outline">
        <span className="font-mono text-[11px]">{trendLabel || detail || ''}</span>
        {detail && trendLabel && <span className={`font-mono text-[11px] ${colors.text}`}>{detail}</span>}
      </div>
    </div>
  )
}
