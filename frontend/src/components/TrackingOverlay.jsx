export default function TrackingOverlay({ persons }) {
  return (
    <>
      {persons.map((person) => {
        const isAbnormal = person.status === 'Abnormal'
        const borderColor = isAbnormal ? 'border-error' : 'border-secondary'
        const bgColor = isAbnormal ? 'bg-error/15' : 'bg-secondary/5'
        const textColor = isAbnormal ? 'text-error' : 'text-secondary'
        const glowShadow = isAbnormal ? 'shadow-[0_0_15px_rgba(255,180,171,0.35)]' : ''

        return (
          <div
            key={person.id}
            className={`absolute pointer-events-none ${isAbnormal ? 'animate-pulse' : ''}`}
            style={{
              top: person.boundingBox.top,
              left: person.boundingBox.left,
              width: person.boundingBox.width,
              height: person.boundingBox.height,
            }}
          >
            {/* Bounding box */}
            <div className={`w-full h-full ${isAbnormal ? 'border-2' : 'border'} ${borderColor} ${bgColor} ${glowShadow} relative`}>
              {/* Corner reticles */}
              <span className={`absolute -top-1 -left-1 w-2.5 h-2.5 border-t-2 border-l-2 ${borderColor}`} />
              <span className={`absolute -top-1 -right-1 w-2.5 h-2.5 border-t-2 border-r-2 ${borderColor}`} />
              <span className={`absolute -bottom-1 -left-1 w-2.5 h-2.5 border-b-2 border-l-2 ${borderColor}`} />
              <span className={`absolute -bottom-1 -right-1 w-2.5 h-2.5 border-b-2 border-r-2 ${borderColor}`} />

              {/* Centroid */}
              {isAbnormal ? (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-error rounded-full animate-ping opacity-40" />
                </div>
              ) : (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-secondary" />
              )}
            </div>

            {/* Floating label */}
            <div className={`absolute -top-7 left-0 bg-surface-container-lowest/90 backdrop-blur px-2 py-0.5 rounded flex items-center gap-1.5 shadow-md whitespace-nowrap ${isAbnormal ? 'border-l-2 border-error' : ''}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isAbnormal ? 'bg-error' : 'bg-secondary'}`} />
              <span className={`font-mono text-[11px] ${textColor} ${isAbnormal ? 'font-semibold' : ''}`}>
                {isAbnormal && '⚠ '}ID #{String(person.id).padStart(2, '0')} • {person.behaviour} ({person.confidence}%) [{person.status.toUpperCase()}]
              </span>
            </div>

            {/* Bottom metadata for abnormal */}
            {isAbnormal && (
              <div className="absolute -bottom-6 left-0 bg-surface-container-lowest/90 px-1.5 py-0.5 rounded font-mono text-[10px] text-on-surface-variant whitespace-nowrap">
                DWELL: {person.dwell} | {person.zone.toUpperCase()}
              </div>
            )}
          </div>
        )
      })}
    </>
  )
}
