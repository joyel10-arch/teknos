import React, { useRef, useEffect } from 'react'

export default function TrackingCanvas({
  tracks = [],
  currentTime = 0,
  resolution = { width: 640, height: 360 },
  showBoundingBoxes = true,
  showTrackingIds = true,
  showTrajectoryPaths = true
}) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Auto fit canvas size to container
    const width = canvas.clientWidth || canvas.parentElement?.clientWidth || 640
    const height = canvas.clientHeight || canvas.parentElement?.clientHeight || 360
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
    }

    ctx.clearRect(0, 0, width, height)

    const resObj = (resolution && typeof resolution === 'object') ? resolution : {}
    const vWidth = Number(resObj.width) || 640
    const vHeight = Number(resObj.height) || 360

    const scaleX = width / vWidth;
    const scaleY = height / vHeight;

    const trackList = Array.isArray(tracks) ? tracks : [];
    trackList.forEach((track) => {
      if (!track.is_valid_track || !track.trajectory || track.trajectory.length === 0) return

      const isAbnormal = track.status === 'Abnormal'
      const mainColor = isAbnormal ? '#ff3366' : '#00f0ff'
      const badgeBg = isAbnormal ? 'rgba(60, 10, 25, 0.85)' : 'rgba(10, 30, 45, 0.85)'

      // Find active point at currentTime
      const trajectory = track.trajectory
      const pastPoints = trajectory.filter(p => p.t <= currentTime && p.t >= currentTime - 3.0)

      if (pastPoints.length === 0) return
      const currentPoint = pastPoints[pastPoints.length - 1]

      // 1. Draw Trajectory Motion Paths
      if (showTrajectoryPaths && pastPoints.length > 1) {
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(pastPoints[0].x * scaleX, pastPoints[0].y * scaleY)

        for (let i = 1; i < pastPoints.length; i++) {
          const pt = pastPoints[i]
          ctx.lineTo(pt.x * scaleX, pt.y * scaleY)
        }

        ctx.strokeStyle = mainColor
        ctx.lineWidth = isAbnormal ? 3.0 : 2.0
        ctx.shadowColor = mainColor
        ctx.shadowBlur = 8
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        ctx.stroke()
        ctx.restore()
      }

      // Check if entity is currently visible (within 0.6s of playhead)
      const isCurrentlyVisible = Math.abs(currentPoint.t - currentTime) < 0.6

      if (isCurrentlyVisible && currentPoint.bbox) {
        const [x1, y1, x2, y2] = currentPoint.bbox
        const bx = x1 * scaleX
        const by = y1 * scaleY
        const bw = Math.max(10, (x2 - x1) * scaleX)
        const bh = Math.max(10, (y2 - y1) * scaleY)

        // 2. Draw Bounding Boxes
        if (showBoundingBoxes) {
          ctx.save()
          ctx.strokeStyle = mainColor
          ctx.lineWidth = isAbnormal ? 2 : 1.5
          ctx.shadowColor = mainColor
          ctx.shadowBlur = isAbnormal ? 10 : 4
          ctx.strokeRect(bx, by, bw, bh)

          // Corner reticles
          const cornerLen = Math.min(12, Math.max(4, Math.min(bw, bh) * 0.2))
          ctx.lineWidth = 2.5
          
          // TL
          ctx.beginPath(); ctx.moveTo(bx, by + cornerLen); ctx.lineTo(bx, by); ctx.lineTo(bx + cornerLen, by); ctx.stroke();
          // TR
          ctx.beginPath(); ctx.moveTo(bx + bw - cornerLen, by); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw, by + cornerLen); ctx.stroke();
          // BL
          ctx.beginPath(); ctx.moveTo(bx, by + bh - cornerLen); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + cornerLen, by + bh); ctx.stroke();
          // BR
          ctx.beginPath(); ctx.moveTo(bx + bw - cornerLen, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by + bh - cornerLen); ctx.stroke();

          // Centroid crosshair
          const cx = bx + bw / 2
          const cy = by + bh / 2
          ctx.fillStyle = mainColor
          ctx.beginPath()
          ctx.arc(cx, cy, 3, 0, Math.PI * 2)
          ctx.fill()
          ctx.restore()
        }

        // 3. Draw Tracking IDs & Labels
        if (showTrackingIds) {
          ctx.save()
          const labelText = `#TRK-${track.track_id} • ${track.behaviour || 'Monitored'}`
          ctx.font = 'bold 11px monospace'
          const textMetrics = ctx.measureText(labelText)
          const textWidth = textMetrics.width
          const textHeight = 14
          const pad = 4

          const badgeX = bx
          const badgeY = Math.max(textHeight + pad * 2, by - textHeight - pad)

          // Badge Background
          ctx.fillStyle = badgeBg
          ctx.strokeStyle = mainColor
          ctx.lineWidth = 1
          ctx.fillRect(badgeX, badgeY - textHeight, textWidth + pad * 2, textHeight + pad)
          ctx.strokeRect(badgeX, badgeY - textHeight, textWidth + pad * 2, textHeight + pad)

          // Badge Text
          ctx.fillStyle = '#ffffff'
          ctx.fillText(labelText, badgeX + pad, badgeY - 2)
          ctx.restore()
        }
      }
    })
  }, [tracks, currentTime, resolution, showBoundingBoxes, showTrackingIds, showTrajectoryPaths])

  return (
    <canvas 
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none w-full h-full z-20"
    />
  )
}
