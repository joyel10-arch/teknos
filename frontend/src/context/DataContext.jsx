import React, { createContext, useContext, useState, useEffect } from 'react'
import { getSummary, getEvents, getTracks, getZones } from '../api/api'

const DataContext = createContext()

export function DataProvider({ children }) {
  const [summary, setSummary] = useState(null)
  const [events, setEvents] = useState([])
  const [tracks, setTracks] = useState([])
  const [zones, setZones] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [uploadedVideo, setUploadedVideo] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [summaryRes, eventsRes, tracksRes, zonesRes] = await Promise.all([
        getSummary(),
        getEvents(),
        getTracks(),
        getZones()
      ])
      setSummary(summaryRes.data)
      setEvents(eventsRes.data)
      setTracks(tracksRes.data)
      setZones(zonesRes.data)
      setError(null)
    } catch (err) {
      console.error("Error fetching data from backend:", err)
      setError(err.message || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <DataContext.Provider value={{ summary, events, tracks, zones, loading, error, uploadedVideo, setUploadedVideo, refreshData: fetchData }}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  return useContext(DataContext)
}
