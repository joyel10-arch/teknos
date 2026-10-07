import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useData } from '../context/DataContext'
import { useMemo } from 'react'

const RADIAN = Math.PI / 180

export default function BehaviourChart() {
  const { summary, events, tracks } = useData()

  const behaviourDistribution = useMemo(() => {
    if (!summary?.event_counts_by_type) {
      return [
        { name: 'Loading Data', value: 100, count: 0, color: '#4cd7f6' }
      ]
    }
    const colors = ['#4cd7f6', '#8c909f', '#ffb4ab', '#4d8eff', '#e2b34a']
    return Object.entries(summary.event_counts_by_type).map(([key, count], index) => {
      // Create a nice human readable name
      const name = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
      return {
        name,
        value: count,
        count: count,
        color: colors[index % colors.length]
      }
    }).filter(d => d.value > 0) // only show ones with occurrences
  }, [summary])

  // Build real hourly/segment timeline from events
  const timelineData = useMemo(() => {
    const eventList = events || []
    const duration = summary?.duration_seconds || 60
    
    if (eventList.length === 0) {
      return [{ segment: '0s', normal: 0, anomaly: 0 }]
    }

    // Create time segments (bins). Use ~10 segments across the video duration.
    const segmentCount = Math.max(4, Math.min(12, Math.ceil(duration / 5)))
    const segmentDuration = duration / segmentCount
    const segments = []
    
    for (let i = 0; i < segmentCount; i++) {
      const segStart = i * segmentDuration
      const segEnd = segStart + segmentDuration
      let normal = 0
      let anomaly = 0
      
      eventList.forEach(evt => {
        const t = evt.start_time_seconds || 0
        if (t >= segStart && t < segEnd) {
          if (evt.severity === 'high' || evt.severity === 'medium') {
            anomaly++
          } else {
            normal++
          }
        }
      })
      
      const label = segStart < 60 
        ? `${Math.floor(segStart)}s` 
        : `${Math.floor(segStart / 60)}m${Math.floor(segStart % 60)}s`
      
      segments.push({ segment: label, normal, anomaly })
    }
    
    return segments
  }, [events, summary])

  // Find peak anomaly segment for annotation
  const peakSegment = useMemo(() => {
    if (!timelineData || timelineData.length === 0) return null
    let maxAnomaly = 0
    let peakLabel = ''
    timelineData.forEach(seg => {
      if (seg.anomaly > maxAnomaly) {
        maxAnomaly = seg.anomaly
        peakLabel = seg.segment
      }
    })
    return maxAnomaly > 0 ? { label: peakLabel, count: maxAnomaly } : null
  }, [timelineData])

  const totalEvents = summary?.total_events || 0

  // Build compliance table from tracks data
  const complianceRows = useMemo(() => {
    const trackList = tracks || []
    const validTracks = trackList.filter(t => t.is_valid_track)
    
    // Group by behaviour
    const groups = {}
    validTracks.forEach(t => {
      const beh = t.behaviour || 'Unknown'
      if (!groups[beh]) groups[beh] = { count: 0, totalSpeed: 0, totalDuration: 0, isAbnormal: false }
      groups[beh].count++
      groups[beh].totalSpeed += Math.abs(t.net_dx || 0)
      groups[beh].totalDuration += t.duration_seconds || 0
      if (t.status === 'Abnormal') groups[beh].isAbnormal = true
    })

    return Object.entries(groups).slice(0, 5).map(([name, data]) => ({
      name,
      avgSpeed: data.count > 0 ? (data.totalSpeed / data.count).toFixed(1) : '0.0',
      avgDuration: data.count > 0 ? formatDuration(data.totalDuration / data.count) : '-',
      isAbnormal: data.isAbnormal,
      count: data.count
    }))
  }, [tracks])

  function formatDuration(seconds) {
    if (seconds < 60) return `${seconds.toFixed(0)}s`
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}m ${s}s`
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Donut Chart: Behaviour Distribution */}
      <div className="bg-surface-container-low p-5 rounded-xl shadow-md flex flex-col">
        <div className="flex items-center justify-between pb-3">
          <div className="flex flex-col">
            <span className="font-mono text-[11px] text-secondary uppercase tracking-wider">CLASSIFICATION BREAKDOWN</span>
            <h2 className="text-[18px] font-semibold text-on-surface">Behaviour Distribution & Activity Breakdown</h2>
          </div>
          <span className="px-2 py-0.5 rounded bg-surface-container-high font-mono text-[11px] text-on-surface-variant">
            {behaviourDistribution.length} CATEGORIES DETECTED
          </span>
        </div>
        <p className="text-[12px] text-on-surface-variant mb-4">Kinematic posture vectors categorized via Spatio-Temporal Graph Convolutional Networks (ST-GCN).</p>

        <div className="grid grid-cols-12 gap-4 items-center bg-surface-container-lowest p-4 rounded-xl mb-4">
          {/* Chart */}
          <div className="col-span-5 flex justify-center">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie
                  data={behaviourDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {behaviourDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute flex flex-col items-center justify-center pointer-events-none" style={{ width: 160, height: 160 }}>
            </div>
          </div>
          {/* Legend */}
          <div className="col-span-7 flex flex-col gap-2">
            {behaviourDistribution.map((item) => (
              <div key={item.name} className="flex items-center justify-between p-1.5 rounded bg-surface-container">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-[12px] text-on-surface">{item.name}</span>
                </div>
                <span className="font-mono text-[14px] font-semibold" style={{ color: item.color }}>
                  {totalEvents > 0 ? ((item.count / totalEvents) * 100).toFixed(1) : 0}% <span className="text-on-surface-variant font-normal text-[11px]">({item.count.toLocaleString()})</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Compliance table - now driven by real track data */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[12px]">
            <thead>
              <tr className="bg-surface-container-high text-on-surface-variant font-mono text-[11px] uppercase">
                <th className="py-1.5 px-2 rounded-l">Class</th>
                <th className="py-1.5 px-2">Avg Speed (px/s)</th>
                <th className="py-1.5 px-2">Mean Duration</th>
                <th className="py-1.5 px-2">Count</th>
                <th className="py-1.5 px-2 rounded-r">Status</th>
              </tr>
            </thead>
            <tbody>
              {complianceRows.map((row, idx) => (
                <tr key={idx} className="hover:bg-surface-container transition-colors">
                  <td className={`py-2 px-2 font-semibold ${row.isAbnormal ? 'text-error' : 'text-on-surface'}`}>{row.name}</td>
                  <td className={`py-2 px-2 font-mono text-[11px] ${row.isAbnormal ? 'text-error' : 'text-secondary'}`}>{row.avgSpeed}</td>
                  <td className="py-2 px-2 font-mono text-[11px] text-on-surface-variant">{row.avgDuration}</td>
                  <td className="py-2 px-2 font-mono text-[11px] text-on-surface">{row.count}</td>
                  <td className="py-2 px-2">
                    <span className={`px-1.5 py-0.5 rounded font-mono text-[11px] font-semibold ${row.isAbnormal ? 'bg-error-container/30 text-error' : 'bg-tertiary/20 text-tertiary'}`}>
                      {row.isAbnormal ? 'FLAGGED' : 'CONFORMANT'}
                    </span>
                  </td>
                </tr>
              ))}
              {complianceRows.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 px-2 text-center text-on-surface-variant">No track data available. Upload a video to see analysis.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bar Chart: Normal vs Abnormal Timeline */}
      <div className="bg-surface-container-low p-5 rounded-xl shadow-md flex flex-col">
        <div className="flex items-center justify-between pb-3">
          <div className="flex flex-col">
            <span className="font-mono text-[11px] text-secondary uppercase tracking-wider">EVENT FREQUENCY HISTOGRAM</span>
            <h2 className="text-[18px] font-semibold text-on-surface">Normal vs Abnormal Events (Video Timeline)</h2>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <span className="flex items-center gap-1 text-on-surface-variant"><span className="w-2.5 h-2.5 rounded-sm bg-secondary" /> Normal</span>
            <span className="flex items-center gap-1 text-error font-semibold"><span className="w-2.5 h-2.5 rounded-sm bg-error" /> Anomaly</span>
          </div>
        </div>
        <p className="text-[12px] text-on-surface-variant mb-3">
          Event distribution across the video timeline. Duration: {summary?.duration_seconds ? `${summary.duration_seconds.toFixed(1)}s` : 'N/A'}.
        </p>

        <div className="flex-1 bg-surface-container-lowest p-3 rounded-xl relative">
          {/* Peak annotation */}
          {peakSegment && (
            <div className="absolute top-3 right-[15%] z-20 flex flex-col items-center pointer-events-none">
              <div className="bg-error text-on-error font-mono text-[11px] px-1.5 py-0.5 rounded shadow-lg font-bold animate-pulse">
                PEAK: {peakSegment.label} (+{peakSegment.count} Anomalies)
              </div>
            </div>
          )}

          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={timelineData} barGap={2}>
              <XAxis
                dataKey="segment"
                tick={{ fill: '#8c909f', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1c1f2a',
                  border: '1px solid #424754',
                  borderRadius: '8px',
                  fontFamily: 'JetBrains Mono',
                  fontSize: '11px',
                }}
                labelStyle={{ color: '#dfe2f1' }}
              />
              <Bar dataKey="normal" fill="#4cd7f6" radius={[2, 2, 0, 0]} opacity={0.8} />
              <Bar dataKey="anomaly" fill="#ffb4ab" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Summary footer */}
        <div className="mt-3 p-3 rounded-xl bg-surface-container flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${(summary?.event_counts_by_severity?.high || 0) > 0 ? 'bg-error' : 'bg-secondary'}`} />
            <div className="flex flex-col">
              <span className="text-[12px] text-on-surface font-semibold">
                {totalEvents} Total Events Detected
              </span>
              <span className="font-mono text-[11px] text-outline">
                {summary?.event_counts_by_severity?.high || 0} High • {summary?.event_counts_by_severity?.medium || 0} Medium • {summary?.event_counts_by_severity?.info || 0} Info
              </span>
            </div>
          </div>
          <span className="px-3 py-1 rounded bg-surface-container-high text-secondary font-mono text-[11px] uppercase">
            {summary?.processing_info?.model_name || 'YOLOv11'} Pipeline
          </span>
        </div>
      </div>
    </div>
  )
}
