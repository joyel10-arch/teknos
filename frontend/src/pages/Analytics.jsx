import { Activity, Camera, Cpu, HardDrive } from 'lucide-react'
import BehaviourChart from '../components/BehaviourChart'
import { useData } from '../context/DataContext'

export default function Analytics() {
  const { summary } = useData()

  const fps = summary?.processing_info?.processing_fps?.toFixed(1) || 0
  const inferenceMs = fps > 0 ? (1000 / fps).toFixed(1) : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-on-surface">Analytics & Insights</h1>
        <p className="text-sm text-on-surface-variant mt-1">
          Behavioural trends, anomaly distribution, and system performance metrics
        </p>
      </div>

      {/* Model Performance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-surface-container p-4 rounded-xl shadow-sm border border-outline-variant/30 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center text-primary">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Avg Inference Time</p>
            <p className="text-xl font-bold text-on-surface font-mono">{inferenceMs} ms</p>
          </div>
        </div>
        <div className="bg-surface-container p-4 rounded-xl shadow-sm border border-outline-variant/30 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center text-primary">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Avg FPS</p>
            <p className="text-xl font-bold text-on-surface font-mono">{fps}</p>
          </div>
        </div>
        <div className="bg-surface-container p-4 rounded-xl shadow-sm border border-outline-variant/30 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-secondary">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Active Cameras</p>
            <p className="text-xl font-bold text-on-surface font-mono">4 / 4</p>
          </div>
        </div>
        <div className="bg-surface-container p-4 rounded-xl shadow-sm border border-outline-variant/30 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-error-container flex items-center justify-center text-error">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-on-surface-variant font-medium uppercase tracking-wider">Storage Retained</p>
            <p className="text-xl font-bold text-on-surface font-mono">7 Days</p>
          </div>
        </div>
      </div>

      {/* Main Charts Component (Reusable from Stitch) */}
      <BehaviourChart />

      {/* Detail Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/30 shadow-md">
           <h3 className="text-sm font-semibold text-on-surface mb-4">Anomaly Heatmap (Zone Activity)</h3>
           <div className="aspect-video bg-surface-container rounded-lg border border-outline-variant/20 relative overflow-hidden flex items-center justify-center group">
              <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1542382103-60580eb7501a?q=80&w=800&auto=format&fit=crop')] bg-cover bg-center opacity-20 group-hover:opacity-30 transition-opacity"></div>
              {/* Simulated Heatmap blobs */}
              <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-error/40 rounded-full blur-2xl"></div>
              <div className="absolute bottom-1/3 right-1/3 w-40 h-40 bg-secondary/30 rounded-full blur-2xl"></div>
              
              <div className="relative z-10 text-center">
                 <p className="text-on-surface font-medium">Zone 2 (Lobby Entrance)</p>
                 <p className="text-error text-xs mt-1">High loitering frequency detected</p>
              </div>
           </div>
        </div>
        
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant/30 shadow-md">
           <h3 className="text-sm font-semibold text-on-surface mb-4">System Event Logs</h3>
           <div className="space-y-3 font-mono text-xs">
              <div className="flex gap-4 items-start p-2 rounded bg-surface-container/50">
                 <span className="text-on-surface-variant shrink-0">14:22:01</span>
                 <span className="text-primary shrink-0">[INFO]</span>
                 <span className="text-on-surface truncate">YOLOv8 Weights reloaded successfully (v8n-pose.pt)</span>
              </div>
              <div className="flex gap-4 items-start p-2 rounded bg-surface-container/50">
                 <span className="text-on-surface-variant shrink-0">14:20:45</span>
                 <span className="text-secondary shrink-0">[WARN]</span>
                 <span className="text-on-surface truncate">CAM-03 latency spike detected (&gt;150ms)</span>
              </div>
              <div className="flex gap-4 items-start p-2 rounded bg-error-container/10 border border-error/20">
                 <span className="text-on-surface-variant shrink-0">14:15:10</span>
                 <span className="text-error shrink-0">[CRIT]</span>
                 <span className="text-on-surface truncate">Multiple loitering events triggered simultaneously in Zone 1</span>
              </div>
              <div className="flex gap-4 items-start p-2 rounded bg-surface-container/50">
                 <span className="text-on-surface-variant shrink-0">14:00:00</span>
                 <span className="text-primary shrink-0">[INFO]</span>
                 <span className="text-on-surface truncate">Hourly log rotation complete (cleared 2.1GB)</span>
              </div>
              <div className="flex gap-4 items-start p-2 rounded bg-surface-container/50">
                 <span className="text-on-surface-variant shrink-0">13:45:22</span>
                 <span className="text-primary shrink-0">[INFO]</span>
                 <span className="text-on-surface truncate">ByteTrack association threshold updated to 0.8</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  )
}
