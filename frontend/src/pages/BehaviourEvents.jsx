import { useState } from 'react'
import { Filter, Download, Calendar, ShieldAlert, CheckCircle2, AlertTriangle, Clock } from 'lucide-react'
import EventTimeline from '../components/EventTimeline'
import { useData } from '../context/DataContext'

export default function BehaviourEvents() {
  const [activeFilter, setActiveFilter] = useState('All')
  const { events, summary } = useData()

  // Derive counts from actual events data
  const eventList = events || []
  const allCount = eventList.length
  const criticalCount = eventList.filter(e => e.severity === 'high').length
  const warningCount = eventList.filter(e => e.severity === 'medium').length
  const normalCount = eventList.filter(e => e.severity === 'info' || e.severity === 'low').length

  const filters = [
    { id: 'All', label: 'All Events', count: allCount, icon: Clock, color: 'text-on-surface' },
    { id: 'Critical', label: 'Critical', count: criticalCount, icon: ShieldAlert, color: 'text-error' },
    { id: 'Warning', label: 'Warnings', count: warningCount, icon: AlertTriangle, color: 'text-secondary' },
    { id: 'Normal', label: 'Normal', count: normalCount, icon: CheckCircle2, color: 'text-primary' },
  ]

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Behaviour Audit Log</h1>
          <p className="text-sm text-on-surface-variant mt-1">
            Historical log of all detected subjects and classified behaviours
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 bg-surface-container hover:bg-surface-container-high text-on-surface border border-outline-variant/30 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            <Calendar className="w-4 h-4" />
            Last 24 Hours
          </button>
          <button className="flex items-center gap-2 bg-primary-container hover:bg-primary-container/80 text-primary-container-foreground px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 p-1 bg-surface-container-lowest border border-outline-variant/30 rounded-lg w-max shadow-sm">
        {filters.map(filter => {
          const Icon = filter.icon
          const isActive = activeFilter === filter.id
          return (
            <button
              key={filter.id}
              onClick={() => setActiveFilter(filter.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                isActive 
                  ? 'bg-surface-container shadow-sm text-on-surface border border-outline-variant/50' 
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-lowest/50 border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${filter.color}`} />
              {filter.label}
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                isActive ? 'bg-outline-variant/20' : 'bg-surface-container'
              }`}>
                {filter.count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Main Table Area */}
      <div className="flex-1 min-h-0 bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-lg overflow-hidden flex flex-col">
        {/* Advanced Filters Bar */}
        <div className="p-4 border-b border-outline-variant/30 bg-surface-container flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <Filter className="w-4 h-4" />
            <span className="text-sm font-medium">Filters:</span>
          </div>
          <select className="bg-surface-container-lowest text-on-surface text-sm border border-outline-variant/30 rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary/50 min-w-[150px]">
            <option>All Cameras</option>
            <option>CAM-01</option>
            <option>CAM-02</option>
          </select>
          <select className="bg-surface-container-lowest text-on-surface text-sm border border-outline-variant/30 rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary/50 min-w-[150px]">
            <option>All Behaviours</option>
            <option>Walking</option>
            <option>Standing</option>
            <option>Loitering</option>
          </select>
          <input 
            type="text" 
            placeholder="Search Track ID..." 
            className="bg-surface-container-lowest text-on-surface text-sm border border-outline-variant/30 rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary/50 flex-1 min-w-[200px]"
          />
        </div>

        {/* Table Content (Reusing EventTimeline component) */}
        <div className="flex-1 overflow-auto p-4">
           {/* In a real app we'd pass the activeFilter down to EventTimeline to filter its internal list */}
          <EventTimeline filter={activeFilter} />
        </div>
      </div>
    </div>
  )
}
