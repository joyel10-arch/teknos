import { Pause, Play, SkipForward, RotateCcw, Volume2, Maximize, Eye, EyeOff } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { getVideoUrl, getRawVideoUrl } from '../api/api'
import { useData } from '../context/DataContext'
import TrackingCanvas from './TrackingCanvas'

export default function VideoAnalyzer({ 
  forcedReticle, 
  showBoundingBoxes = true, 
  showTrackingIds = true, 
  showTrajectoryPaths = true 
}) {
  const [isPlaying, setIsPlaying] = useState(true)
  const videoRef = useRef(null)
  const { summary, tracks, uploadedVideo } = useData()
  const [aiReticle, setAiReticle] = useState(true)
  const isReticleActive = forcedReticle !== undefined ? forcedReticle : aiReticle
  const [videoSource, setVideoSource] = useState('')
  const [currentTimeSec, setCurrentTimeSec] = useState(0)

  // Sync video source whenever uploaded video, summary, or AI reticle toggle changes
  useEffect(() => {
    const timestamp = Date.now()
    if (isReticleActive) {
      setVideoSource(`${getVideoUrl()}?t=${timestamp}`)
    } else {
      setVideoSource(`${getRawVideoUrl()}?t=${timestamp}`)
    }
  }, [uploadedVideo, summary, isReticleActive])

  const [playheadPosition, setPlayheadPosition] = useState(0)
  const [currentTime, setCurrentTime] = useState('00:00:00')
  const duration = summary?.duration_seconds || 57

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) videoRef.current.pause()
      else videoRef.current.play()
      setIsPlaying(!isPlaying)
    }
  }

  const reloadVideo = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0
      videoRef.current.play()
      setIsPlaying(true)
    }
  }

  const skipForward = () => {
    if (videoRef.current) {
      videoRef.current.currentTime += 5
    }
  }

  const handleTimelineClick = (e) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect()
      const clickX = e.clientX - rect.left
      const percentage = clickX / rect.width
      videoRef.current.currentTime = percentage * duration
    }
  }

  const [playbackSpeed, setPlaybackSpeed] = useState(1.0)
  const changeSpeed = (speed) => {
    if (videoRef.current) {
      videoRef.current.playbackRate = speed
      setPlaybackSpeed(speed)
    }
  }

  const formatTime = (secs) => {
    if (!secs) return '00:00:00'
    const d = new Date(secs * 1000)
    return d.toISOString().substr(11, 8)
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const current = videoRef.current.currentTime
      setCurrentTimeSec(current)
      setPlayheadPosition((current / duration) * 100)
      setCurrentTime(formatTime(current))
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Video Viewport */}
      <div className="relative w-full bg-surface-container-lowest rounded-lg overflow-hidden shadow-xl select-none group">
        {/* 16:9 Video area */}
        <div className="relative aspect-video w-full bg-black overflow-hidden flex justify-center items-center">
          
          <video 
            ref={videoRef}
            src={videoSource} 
            autoPlay 
            muted 
            loop 
            key={videoSource}
            className="w-full h-full object-contain"
            onTimeUpdate={handleTimeUpdate}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />

          {/* Interactive HTML5 Canvas Overlay for Bounding Boxes, Tracking IDs, and Trajectory Paths */}
          {isReticleActive && (
            <TrackingCanvas 
              tracks={tracks}
              currentTime={currentTimeSec}
              resolution={summary?.resolution || { width: 640, height: 360 }}
              showBoundingBoxes={showBoundingBoxes}
              showTrackingIds={showTrackingIds}
              showTrajectoryPaths={showTrajectoryPaths}
            />
          )}

          {/* Top HUD bar */}
          <div className="absolute top-0 left-0 right-0 p-3 flex items-center justify-between pointer-events-none z-30">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 bg-surface-container-lowest/85 backdrop-blur-md px-2 py-0.5 rounded text-error font-mono text-[11px]">
                <span className="w-2 h-2 rounded-full bg-error animate-ping" /> REC
              </span>
              <span className="bg-surface-container-lowest/85 backdrop-blur-md px-2 py-0.5 rounded text-on-surface font-mono text-[11px]">
                {summary?.video_id || 'AI_FEED'} // {summary?.resolution?.width || 640}x{summary?.resolution?.height || 360}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded font-mono text-[11px] shadow-sm transition-colors ${isReticleActive ? 'bg-error-container/80 text-on-error-container backdrop-blur-md' : 'bg-surface-container/80 text-on-surface-variant'}`}>
                {isReticleActive ? 'AI RETICLE ACTIVE' : 'RAW FEED'}
              </span>
              <span className="bg-surface-container-lowest/85 backdrop-blur-md px-2 py-0.5 rounded text-tertiary font-mono text-[11px]">
                FPS: {summary?.fps ? Math.round(summary.fps) : 30}
              </span>
            </div>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="w-full bg-surface-container-low px-3 py-2 flex flex-col gap-1.5">
          {/* Timeline scrubber */}
          <div className="relative w-full h-7 flex items-center cursor-pointer" onClick={handleTimelineClick}>
            <div className="w-full h-2 bg-surface-container-high rounded-full overflow-hidden relative pointer-events-none">
              <div className="absolute left-0 top-0 bottom-0 w-[84%] bg-surface-container-highest" />
              <div className="absolute left-[5%] top-0 bottom-0 w-[18%] bg-tertiary/40" />
              <div className="absolute left-[26%] top-0 bottom-0 w-[24%] bg-tertiary/40" />
              <div className="absolute left-[36%] top-0 bottom-0 w-[8%] bg-error/90 animate-pulse" />
              <div className="absolute left-0 top-0 bottom-0 bg-primary/70" style={{ width: `${playheadPosition}%` }} />
            </div>
            {/* Anomaly flag */}
            <div className="absolute left-[36%] -top-1 -translate-x-1/2 flex flex-col items-center pointer-events-none">
              <div className="bg-error text-on-error font-mono text-[9px] px-1 rounded shadow font-bold">{formatTime(duration * 0.36)} ABNORMAL</div>
              <div className="w-0.5 h-3 bg-error" />
            </div>
            {/* Playhead */}
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-primary-fixed rounded-full shadow-lg border-2 border-surface" style={{ left: `${playheadPosition}%` }}>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-on-primary-fixed rounded-full" />
            </div>
          </div>

          {/* Control buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={togglePlay} className="w-8 h-8 rounded bg-primary text-on-primary flex items-center justify-center hover:bg-primary-fixed transition-colors shadow-sm">
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              </button>
              <button onClick={reloadVideo} className="w-8 h-8 rounded bg-surface-container hover:bg-surface-container-high text-on-surface flex items-center justify-center transition-colors">
                <RotateCcw className="w-[18px] h-[18px]" />
              </button>
              <button onClick={skipForward} className="w-8 h-8 rounded bg-surface-container hover:bg-surface-container-high text-on-surface flex items-center justify-center transition-colors">
                <SkipForward className="w-[18px] h-[18px]" />
              </button>
              <div className="ml-1 font-mono text-[14px] flex items-center gap-1">
                <span className="text-secondary font-semibold">{currentTime}</span>
                <span className="text-outline">/</span>
                <span className="text-on-surface-variant">{formatTime(duration)}</span>
              </div>
            </div>

            {/* Speed controls */}
            <div className="hidden md:flex items-center gap-1 bg-surface-container-lowest px-2 py-1 rounded">
              <span className="font-mono text-[10px] text-outline uppercase px-1">SPEED</span>
              {[0.5, 1.0, 1.5, 2.0].map((speed) => (
                <button 
                  key={speed} 
                  onClick={() => changeSpeed(speed)}
                  className={`px-1.5 py-0.5 rounded font-mono text-[11px] ${playbackSpeed === speed ? 'bg-surface-container-high text-secondary font-semibold shadow-inner' : 'text-on-surface-variant hover:text-on-surface'}`}
                >
                  {speed.toFixed(1)}x
                </button>
              ))}
            </div>

            {/* Right controls */}
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setAiReticle(!aiReticle)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded transition-all font-mono text-[11px] font-semibold ${isReticleActive ? 'bg-primary text-on-primary shadow-md' : 'bg-surface-container text-on-surface-variant hover:text-on-surface'}`}
              >
                {isReticleActive ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                <span>AI RETICLE</span>
              </button>
              <button className="p-1.5 text-on-surface-variant hover:text-on-surface transition-colors">
                <Volume2 className="w-5 h-5" />
              </button>
              <button className="p-1.5 text-on-surface-variant hover:text-on-surface transition-colors">
                <Maximize className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline metadata bar */}
      <div className="w-full bg-surface-container-low rounded-lg p-3 flex flex-wrap items-center justify-between gap-2 shadow-sm">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-[11px] text-outline uppercase tracking-wider">Active Pipeline:</span>
          <span className="font-mono text-[11px] text-on-surface bg-surface-container px-1.5 py-0.5 rounded">YOLOv11 (Object Detection)</span>
          <span className="text-outline text-[11px]">+</span>
          <span className="font-mono text-[11px] text-secondary bg-surface-container px-1.5 py-0.5 rounded">ByteTrack (Multi-Target Tracking)</span>
          <span className="text-outline text-[11px]">+</span>
          <span className="font-mono text-[11px] text-tertiary bg-surface-container px-1.5 py-0.5 rounded">Temporal Behaviour Engine</span>
        </div>
        <div className="flex items-center gap-4 font-mono text-[11px] text-on-surface-variant tracking-wider">
          <span>BATCH: <strong className="text-on-surface">1</strong></span>
          <span>LATENCY: <strong className="text-tertiary">18.2 ms</strong></span>
          <span>STATUS: <strong className="text-secondary">REAL-TIME ACTIVE</strong></span>
        </div>
      </div>
    </div>
  )
}
