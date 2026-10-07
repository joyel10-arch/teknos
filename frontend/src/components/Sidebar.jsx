import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Video, AlertTriangle, BarChart3, Cpu, ShieldCheck } from 'lucide-react'
import BackendStatus from './BackendStatus'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/video-analysis', label: 'Video Analysis', icon: Video },
  { path: '/behaviour-events', label: 'Behaviour Events', icon: AlertTriangle },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="fixed left-0 top-0 h-full w-[280px] bg-surface-container-low z-50 flex flex-col justify-between shadow-[0_1px_8px_rgba(0,0,0,0.4)]">
      {/* Top: Logo + Nav */}
      <div className="flex flex-col">
        {/* Brand */}
        <div className="p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary-container flex items-center justify-center">
            <Cpu className="w-5 h-5 text-on-primary" />
          </div>
          <div className="flex flex-col">
            <span className="text-[15px] font-semibold uppercase tracking-wider text-on-surface">Autonomous Vision</span>
            <span className="font-mono text-[11px] text-secondary uppercase bg-surface-container-high px-1 py-0.5 rounded tracking-wider w-fit">
              Behaviour Intelligence v2.4
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 px-3 mt-3">
          {navItems.map(({ path, label, icon: Icon }) => {
            const isActive = location.pathname === path
            return (
              <NavLink
                key={path}
                to={path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors text-[13px] ${
                  isActive
                    ? 'bg-primary-container text-on-primary-container font-semibold'
                    : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                }`}
              >
                <Icon className="w-[18px] h-[18px]" />
                {label}
              </NavLink>
            )
          })}
        </nav>
      </div>

      {/* Bottom: Status + User */}
      <div className="p-3 flex flex-col gap-3 bg-surface-container-lowest">
        {/* Storage */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between font-mono text-[11px] text-on-surface-variant tracking-wider">
            <span>STORAGE USE</span>
            <span className="text-on-surface font-medium">78% / 4.2 TB</span>
          </div>
          <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
            <div className="h-full bg-secondary rounded-full" style={{ width: '78%' }} />
          </div>
        </div>

        {/* Backend Status */}
        <BackendStatus />

        {/* User */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface text-[14px] font-semibold">
              SA
            </div>
            <div className="flex flex-col">
              <span className="text-[12px] text-on-surface font-semibold">Security Operative</span>
              <span className="font-mono text-[11px] text-outline tracking-wider">System Admin</span>
            </div>
          </div>
          <ShieldCheck className="w-[18px] h-[18px] text-outline" />
        </div>
      </div>
    </aside>
  )
}
