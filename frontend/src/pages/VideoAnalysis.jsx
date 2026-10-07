import { useState, useMemo } from 'react'
import { Camera, Settings2, SlidersHorizontal, EyeOff, Maximize, Play, Download, Search, CheckCircle } from 'lucide-react'
import VideoAnalyzer from '../components/VideoAnalyzer'
import { useData } from '../context/DataContext'

export default function VideoAnalysis() {
  const [selectedCamera, setSelectedCamera] = useState('CAM-01')
  const [showOverlays, setShowOverlays] = useState(true)
  const [showBoundingBoxes, setShowBoundingBoxes] = useState(true)
  const [showTrackingIds, setShowTrackingIds] = useState(true)
  const [showTrajectoryPaths, setShowTrajectoryPaths] = useState(true)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.45)
  const { tracks, summary } = useData()

  // Map backend tracks to the frontend format
  const mappedTracks = useMemo(() => {
    return (tracks || [])
      .filter(t => t.is_valid_track && t.mean_detection_confidence >= confidenceThreshold)
      .map(t => ({
        id: t.track_id,
        trackId: `#TRK-${t.track_id}`,
        label: t.entity_id,
        behaviour: t.behaviour || 'Monitored',
        status: t.status || 'Normal',
        speed: `${Math.abs(t.net_dx / (t.duration_seconds || 1)).toFixed(1)} px/s`,
        dwell: t.dwell || `${t.duration_seconds?.toFixed(1) || 0}s`,
        confidence: (t.mean_detection_confidence * 100).toFixed(1),
    }))
  }, [tracks, confidenceThreshold])

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Top Control Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface-container p-4 rounded-xl shadow-sm border border-outline-variant/20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-on-surface font-medium">
            <Camera className="w-5 h-5 text-primary" />
            <h2>Live Inspection Workspace</h2>
          </div>
          <div className="h-6 w-px bg-outline-variant/30"></div>
          <select 
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value)}
            className="bg-surface-container-lowest text-on-surface text-sm border border-outline-variant/30 rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary/50"
          >
            <option value="CAM-01">CAM-01 (Main Entrance)</option>
            <option value="CAM-02">CAM-02 (Hallway A)</option>
            <option value="CAM-03">CAM-03 (Loading Dock)</option>
            <option value="CAM-04">CAM-04 (Cafeteria)</option>
          </select>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-surface-container-lowest rounded-lg px-3 py-1.5 border border-outline-variant/30">
            <Settings2 className="w-4 h-4 text-on-surface-variant" />
            <span className="text-xs text-on-surface">Model: YOLOv8-Pose</span>
          </div>
          <button className="flex items-center gap-2 bg-secondary-container hover:bg-secondary-container/80 text-secondary-container-foreground px-3 py-1.5 rounded-lg text-xs font-medium transition-colors">
            <Download className="w-4 h-4" />
            Export Frame
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
        {/* Left Side: Pipeline Controls (1 Col) */}
        <div className="bg-surface-container-low p-4 rounded-xl shadow-md border border-outline-variant/20 flex flex-col gap-6 overflow-y-auto">
          <div>
            <h3 className="text-sm font-semibold text-on-surface mb-3 flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-primary" />
              Vision Pipeline Config
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-on-surface-variant">Confidence Threshold</span>
                  <span className="text-primary font-mono">{(confidenceThreshold * 100).toFixed(0)}%</span>
                </div>
                <input 
                  type="range" 
                  min="10" max="95" 
                  value={confidenceThreshold * 100}
                  onChange={(e) => setConfidenceThreshold(e.target.value / 100)}
                  className="w-full h-1.5 bg-outline-variant/30 rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-on-surface-variant">IoU Threshold (NMS)</span>
                  <span className="text-primary font-mono">0.45</span>
                </div>
                <input 
                  type="range" 
                  min="10" max="95" 
                  defaultValue="45"
                  className="w-full h-1.5 bg-outline-variant/30 rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-on-surface-variant">Loitering Time Limit</span>
                  <span className="text-error font-mono">15 sec</span>
                </div>
                <input 
                  type="range" 
                  min="5" max="60" 
                  defaultValue="15"
                  className="w-full h-1.5 bg-outline-variant/30 rounded-lg appearance-none cursor-pointer accent-error"
                />
              </div>
            </div>
          </div>

          <div className="h-px bg-outline-variant/20 w-full"></div>

          <div>
            <h3 className="text-sm font-semibold text-on-surface mb-3">Render Settings</h3>
            <div className="space-y-2">
              <label className="flex items-center gap-3 p-2 hover:bg-surface-container rounded-lg cursor-pointer transition-colors">
                <input 
                  type="checkbox" 
                  checked={showBoundingBoxes} 
                  onChange={(e) => setShowBoundingBoxes(e.target.checked)}
                  className="w-4 h-4 rounded text-primary bg-surface-container-lowest border-outline focus:ring-primary focus:ring-offset-surface"
                />
                <span className="text-sm text-on-surface-variant">Bounding Boxes</span>
              </label>
              <label className="flex items-center gap-3 p-2 hover:bg-surface-container rounded-lg cursor-pointer transition-colors">
                <input 
                  type="checkbox" 
                  checked={showTrackingIds}
                  onChange={(e) => setShowTrackingIds(e.target.checked)}
                  className="w-4 h-4 rounded text-primary bg-surface-container-lowest border-outline focus:ring-primary focus:ring-offset-surface"
                />
                <span className="text-sm text-on-surface-variant">Tracking IDs</span>
              </label>
              <label className="flex items-center gap-3 p-2 hover:bg-surface-container rounded-lg cursor-pointer transition-colors">
                <input 
                  type="checkbox" 
                  checked={showTrajectoryPaths}
                  onChange={(e) => setShowTrajectoryPaths(e.target.checked)}
                  className="w-4 h-4 rounded text-primary bg-surface-container-lowest border-outline focus:ring-primary focus:ring-offset-surface"
                />
                <span className="text-sm text-on-surface-variant">Trajectory Paths</span>
              </label>
            </div>
          </div>
          
          <div className="mt-auto pt-4 border-t border-outline-variant/20">
            <div className="bg-primary-container/20 border border-primary/20 rounded-lg p-3 text-xs text-on-surface-variant">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-primary">System Status</span>
                <CheckCircle className="w-3.5 h-3.5 text-primary" />
              </div>
              <p>Hardware Accel: TensorRT</p>
              <p>Memory Usage: 4.2 GB / 12 GB</p>
            </div>
          </div>
        </div>

        {/* Center: Main Video Player (2 Cols) */}
        <div className="lg:col-span-2 h-full flex flex-col bg-black/40 rounded-xl overflow-hidden border border-outline-variant/30 shadow-2xl relative">
          <div className="absolute top-4 left-4 z-10 flex gap-2">
             <span className="px-2 py-1 bg-surface/80 backdrop-blur-md text-on-surface text-xs font-mono rounded border border-outline/50 shadow-lg">
                FPS: 32.4
             </span>
             <span className="px-2 py-1 bg-surface/80 backdrop-blur-md text-on-surface text-xs font-mono rounded border border-outline/50 shadow-lg flex items-center gap-1">
                <EyeOff className="w-3 h-3 text-on-surface-variant" /> {(showBoundingBoxes || showTrackingIds || showTrajectoryPaths) ? 'HUD ON' : 'HUD OFF'}
             </span>
          </div>
          <div className="flex-1 min-h-0 bg-surface-container-lowest">
            <VideoAnalyzer 
              showBoundingBoxes={showBoundingBoxes} 
              showTrackingIds={showTrackingIds} 
              showTrajectoryPaths={showTrajectoryPaths} 
            />
          </div>
        </div>

        {/* Right Side: Object Log (1 Col) */}
        <div className="bg-surface-container-low rounded-xl shadow-md border border-outline-variant/20 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-outline-variant/20 bg-surface-container">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-on-surface flex items-center gap-2">
                <Search className="w-4 h-4 text-on-surface-variant" />
                Active Objects
              </h3>
              <span className="bg-primary/20 text-primary text-xs font-bold px-2 py-0.5 rounded-full">
                {mappedTracks.length}
              </span>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {mappedTracks.map(person => (
              <div 
                key={person.id} 
                className={`p-3 rounded-lg border flex flex-col gap-2 transition-colors cursor-pointer hover:bg-surface-container-high ${
                  person.status === 'Abnormal' 
                    ? 'bg-error-container/10 border-error/30 hover:border-error/50' 
                    : 'bg-surface-container-lowest border-outline-variant/30'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-mono text-xs font-semibold text-on-surface">{person.trackId}</span>
                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                    person.status === 'Abnormal' ? 'bg-error text-on-error' : 'bg-secondary text-on-secondary'
                  }`}>
                    {person.status}
                  </span>
                </div>
                
                <div className="flex justify-between items-center text-xs">
                  <span className="text-on-surface-variant">{person.behaviour}</span>
                  <span className="font-mono text-on-surface">{person.speed}</span>
                </div>
                
                <div className="w-full bg-surface-container h-1.5 rounded-full overflow-hidden mt-1">
                  <div 
                    className={`h-full rounded-full ${person.status === 'Abnormal' ? 'bg-error' : 'bg-primary'}`} 
                    style={{ width: `${person.confidence}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[10px] text-on-surface-variant/70">
                  <span>Confidence</span>
                  <span>{person.confidence}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
