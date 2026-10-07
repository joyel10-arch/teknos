import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Dashboard from './pages/Dashboard'
import VideoAnalysis from './pages/VideoAnalysis'
import BehaviourEvents from './pages/BehaviourEvents'
import Analytics from './pages/Analytics'
import { DataProvider } from './context/DataContext'

export default function App() {
  return (
    <DataProvider>
      <div className="flex h-screen overflow-hidden bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col ml-[280px]">
        <Header />
        <main className="flex-1 overflow-y-auto pt-16 px-6 pb-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/video-analysis" element={<VideoAnalysis />} />
            <Route path="/behaviour-events" element={<BehaviourEvents />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        </div>
      </div>
    </DataProvider>
  )
}
