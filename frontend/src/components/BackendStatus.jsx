import { useState, useEffect } from 'react'
import { getHealth } from '../api/api'

export default function BackendStatus() {
  const [isConnected, setIsConnected] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    let interval
    const checkHealth = async () => {
      try {
        await getHealth()
        setIsConnected(true)
      } catch {
        setIsConnected(false)
      } finally {
        setChecking(false)
      }
    }

    checkHealth()
    interval = setInterval(checkHealth, 15000) // check every 15s
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center justify-between px-2 py-1.5 bg-surface-container rounded">
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-tertiary' : 'bg-error'} ${checking ? 'animate-pulse' : ''}`} />
        <span className="font-mono text-[11px] text-on-surface tracking-wider">
          {checking ? 'Checking...' : isConnected ? 'GPU Cluster 04' : 'Backend Offline'}
        </span>
      </div>
      <span className={`font-mono text-[11px] tracking-wider ${isConnected ? 'text-tertiary' : 'text-error'}`}>
        {checking ? '...' : isConnected ? 'Online' : 'Mock Data'}
      </span>
    </div>
  )
}
