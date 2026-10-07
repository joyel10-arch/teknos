import { useState } from 'react'
import { Users, Eye, AlertTriangle, Activity, Upload, Play, ShieldAlert, Cpu } from 'lucide-react'
import StatCard from '../components/StatCard'
import VideoAnalyzer from '../components/VideoAnalyzer'
import ActivityPanel from '../components/ActivityPanel'
import AlertCard from '../components/AlertCard'
import UploadModal from '../components/UploadModal'
import EventTimeline from '../components/EventTimeline'
import { useData } from '../context/DataContext'
// import { dashboardStats, securityAlerts as activeAlerts } from '../data/mockData'

export default function Dashboard() {
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const { summary, events, loading } = useData()

  if (loading) {
    return <div className="p-8 text-center text-on-surface">Loading Dashboard...</div>
  }

  // Derive stats from backend summary
  const totalTracked = summary?.valid_tracked_persons || 0
  const activePersons = summary?.raw_track_ids || 0
  const anomaliesDetected = summary?.event_counts_by_severity?.high || 0
  const averageFps = summary?.processing_info?.processing_fps?.toFixed(1) || 0

  // Filter high severity events to show as active alerts
  const activeAlerts = (events || []).filter(e => e.severity === 'high').slice(0, 3).map(e => ({
    id: e.event_id,
    personLabel: e.entity_id,
    camera: 'CAM-01',
    title: e.reason,
    anomalyScore: e.confidence * 100,
    dwell: `${e.duration_seconds || 0}s`,
    timestamp: e.start_time_seconds != null ? new Date(e.start_time_seconds * 1000).toISOString().substring(11, 19) : '00:00:00',
    status: 'ACTION REQUIRED',
    statusColor: 'error',
    eventId: e.event_id,
    trackId: e.track_id,
    zoneName: e.zone_name,
    eventType: e.event_type
  }))

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-gradient-to-r from-surface-container-low via-surface-container to-surface-container-low p-5 rounded-xl border border-outline-variant/30 shadow-md">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <h1 className="text-xl font-bold text-on-surface tracking-tight">System Live Monitor</h1>
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            Real-time multi-person tracking & loitering anomaly detection pipeline (YOLOv8 + ByteTrack)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-on-primary font-medium text-xs rounded-lg shadow-lg shadow-primary/25 transition-all duration-200 cursor-pointer"
          >
            <Upload className="w-4 h-4" />
            <span>Upload New Video</span>
          </button>
        </div>
      </div>

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Tracked Subjects"
          value={totalTracked}
          icon={Users}
          trend="Live"
          trendLabel="valid tracks"
          description="Active tracking instances across video"
          accentColor="primary"
        />
        <StatCard
          label="Active Subjects (Raw)"
          value={activePersons}
          icon={Eye}
          trend="Total"
          trendLabel="raw tracks"
          description="Total raw bounding box tracks"
          accentColor="secondary"
        />
        <StatCard
          label="Anomalies Detected"
          value={anomaliesDetected}
          icon={AlertTriangle}
          trend={`${anomaliesDetected} high`}
          trendLabel="requires action"
          description="High severity threshold violations"
          accentColor="error"
          badge="Critical"
        />
        <StatCard
          label="Average Processing FPS"
          value={`${averageFps} FPS`}
          icon={Cpu}
          trend="Offline"
          trendLabel="processing"
          description={`Model: ${summary?.processing_info?.model_name || 'N/A'}`}
          accentColor="tertiary"
        />
      </div>

      {/* Main Content Grid: Video Feed (Left) & Real-Time Stream (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Surveillance Workspace (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-4 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                <h2 className="text-base font-semibold text-on-surface">Live CCTV Feed — Main Entrance (CAM-01)</h2>
              </div>
              <span className="text-xs px-2.5 py-1 bg-primary-container/40 text-primary-container font-mono rounded-md border border-primary/20">
                1920x1080 @ 30fps
              </span>
            </div>
            <VideoAnalyzer />
          </div>

          {/* Event Timeline Table */}
          <EventTimeline />
        </div>

        {/* Right Sidebar: Real-Time Subject Stream & Alert Feed (1 Col) */}
        <div className="space-y-6">
          {/* Active Alert Banner */}
          {activeAlerts.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-error text-xs font-semibold uppercase tracking-wider">
                <ShieldAlert className="w-4 h-4" />
                <span>Active Anomalies ({activeAlerts.length})</span>
              </div>
              {activeAlerts.map((alert) => (
                <AlertCard key={alert.id} alert={alert} />
              ))}
            </div>
          )}

          {/* Live Activity Matrix */}
          <ActivityPanel />
        </div>
      </div>

      {/* Upload Video Modal */}
      <UploadModal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} />
    </div>
  )
}
