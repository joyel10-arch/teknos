import { useState, useRef } from 'react'
import { Upload, X, FileVideo, Play } from 'lucide-react'
import { useData } from '../context/DataContext'
import { uploadVideo } from '../api/api'

export default function UploadModal({ isOpen, onClose }) {
  const { setUploadedVideo, refreshData } = useData()
  const [selectedFile, setSelectedFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusText, setStatusText] = useState('')
  const fileInputRef = useRef(null)

  if (!isOpen) return null

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true) }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (isProcessing) return
    const file = e.dataTransfer.files[0]
    if (file && isVideoFile(file)) setSelectedFile(file)
  }

  const isVideoFile = (file) => {
    const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/webm', 'video/x-msvideo']
    return validTypes.includes(file.type) || /\.(mp4|avi|mov|webm)$/i.test(file.name)
  }

  const handleFileSelect = (e) => {
    if (isProcessing) return
    const file = e.target.files[0]
    if (file) setSelectedFile(file)
  }

  const startAnalysis = async () => {
    if (!selectedFile) return
    setIsProcessing(true)
    setProgress(5)
    setStatusText('Uploading surveillance video to AI backend...')

    try {
      await uploadVideo(selectedFile, (uploadPct) => {
        const mappedProgress = Math.min(45, Math.max(5, Math.round(uploadPct * 0.45)))
        setProgress(mappedProgress)
        if (uploadPct >= 100) {
          setStatusText('Running YOLO Object Detection & ByteTrack...')
        }
      })

      setProgress(65)
      setStatusText('Processing trajectories & behavioural rules...')
      await new Promise(r => setTimeout(r, 600))

      setProgress(85)
      setStatusText('Rendering AI Reticle annotated stream...')
      await new Promise(r => setTimeout(r, 600))

      setProgress(100)
      setStatusText('Analysis Complete!')

      setTimeout(async () => {
        setIsProcessing(false)
        setUploadedVideo(selectedFile)
        setSelectedFile(null)
        if (refreshData) {
          await refreshData()
        }
        onClose()
      }, 800)
    } catch (err) {
      console.error('Error processing uploaded video:', err)
      setStatusText(`Error: ${err.response?.data?.detail || err.message || 'Processing failed'}`)
      setTimeout(() => {
        setIsProcessing(false)
      }, 3000)
    }
  }

  const formatSize = (bytes) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-slide-up" onClick={onClose}>
      <div className="w-full max-w-lg bg-surface-container-low rounded-xl shadow-2xl border border-outline-variant/30 p-6" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-[18px] font-semibold text-on-surface">Upload Surveillance Video</h2>
            <p className="text-[12px] text-on-surface-variant mt-0.5">Drop local RTSP/MP4 feed to trigger multi-stream analysis</p>
          </div>
          <button onClick={() => !isProcessing && onClose()} className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Dropzone or Selected File */}
        {!selectedFile ? (
          <div
            className={`border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer ${
              isDragging ? 'border-primary bg-primary/5' : 'border-outline-variant hover:border-secondary hover:bg-surface-container/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragging ? 'text-primary' : 'text-secondary'}`} />
            <p className="text-[15px] text-on-surface font-medium mb-1">Drag & drop your video here or browse files</p>
            <p className="text-[12px] text-on-surface-variant">Supported formats: MP4, AVI, MOV, WebM</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.avi,.mov,.webm,video/*"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        ) : (
          <div className="bg-surface-container rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-surface-container-highest flex items-center justify-center text-primary">
                <FileVideo className="w-6 h-6" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[14px] text-on-surface font-semibold truncate">{selectedFile.name}</p>
                <div className="flex items-center gap-3 mt-0.5 font-mono text-[11px] text-on-surface-variant">
                  <span>SIZE: <strong className="text-on-surface">{formatSize(selectedFile.size)}</strong></span>
                  <span className="px-1.5 py-0.5 rounded bg-tertiary-container/30 text-tertiary">READY</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="p-1.5 rounded-lg hover:bg-surface-container-high text-on-surface-variant hover:text-error transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Supported Formats */}
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="font-mono text-[11px] text-outline bg-surface-container-highest px-2 py-1 rounded tracking-wider">MP4, AVI, MOV, WEBM</span>
        </div>

        {/* Actions or Progress */}
        {isProcessing ? (
          <div className="mt-6 flex flex-col gap-3">
            <div className="flex justify-between items-center text-[12px] font-mono font-medium">
              <span className="text-primary animate-pulse">{statusText}</span>
              <span className="text-on-surface">{progress}%</span>
            </div>
            <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-[11px] text-on-surface-variant text-center mt-2">
              Please do not close this window while analysis is running...
            </p>
          </div>
        ) : selectedFile ? (
          <div className="flex items-center gap-3 mt-5">
            <button
              onClick={() => setSelectedFile(null)}
              className="flex-1 py-2.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-[13px] font-medium transition-colors"
            >
              Remove
            </button>
            <button
              onClick={startAnalysis}
              className="flex-1 py-2.5 rounded-lg bg-primary-container text-on-primary-container hover:bg-primary transition-all text-[13px] font-semibold flex items-center justify-center gap-2 shadow-md"
            >
              <Play className="w-4 h-4" />
              Start Analysis
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
