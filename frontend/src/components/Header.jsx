import { Bell, Settings, User, ChevronDown, Video } from 'lucide-react'

export default function Header() {
  return (
    <header className="fixed top-0 left-[280px] right-0 h-16 bg-surface/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.3)] z-40">
      <div className="h-16 w-full px-6 flex items-center justify-between">
        {/* Left: Model info badges */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {/* Model badge */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container font-mono text-[11px] text-on-surface-variant tracking-wider">
              <span className="text-outline">MODEL:</span>
              <span className="text-on-surface">YOLOv9-Behaviour-v2</span>
            </div>
            {/* FPS badge */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container font-mono text-[11px] text-on-surface-variant tracking-wider">
              <span className="text-outline">FPS:</span>
              <span className="text-secondary">29.8</span>
            </div>
            {/* AI Engine status */}
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container font-mono text-[11px] text-tertiary tracking-wider">
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
              AI Engine Online
            </div>
          </div>
        </div>

        {/* Right: Camera selector + actions */}
        <div className="flex items-center gap-3">
          {/* Camera selector */}
          <div className="flex items-center gap-1.5 bg-surface-container-high px-2.5 py-1.5 rounded text-[12px] text-on-surface cursor-pointer hover:bg-surface-container-highest transition-colors">
            <Video className="w-4 h-4 text-secondary" />
            <span className="font-mono text-[11px] tracking-wider">CAM 07 - Warehouse Floor A</span>
            <ChevronDown className="w-4 h-4 text-outline" />
          </div>

          {/* Notifications */}
          <div className="relative flex items-center justify-center p-1.5 text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer">
            <Bell className="w-5 h-5" />
            <span className="absolute top-0.5 right-0.5 w-2.5 h-2.5 rounded-full bg-error ring-2 ring-surface" />
          </div>

          {/* Settings */}
          <div className="flex items-center justify-center p-1.5 text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer">
            <Settings className="w-5 h-5" />
          </div>

          {/* User avatar */}
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
            <User className="w-[18px] h-[18px] text-on-primary" />
          </div>
        </div>
      </div>
    </header>
  )
}
