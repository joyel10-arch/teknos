import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/** Check backend health */
export async function getHealth() {
  return api.get('/api/health')
}

/** Get system summary data */
export async function getSummary() {
  return api.get('/api/summary')
}

/** Get all behaviour events */
export async function getEvents() {
  return api.get('/api/events')
}

/** Get all tracked objects */
export async function getTracks() {
  return api.get('/api/tracks')
}

/** Get configured detection zones */
export async function getZones() {
  return api.get('/api/zones')
}

/** 
 * Video and Evidence are accessed directly via URLs 
 * so we just provide helper functions to get their URLs
 */
export function getVideoUrl() {
  return `${API_BASE_URL}/api/video`
}

export function getRawVideoUrl() {
  return `${API_BASE_URL}/api/raw_video`
}

export function getEvidenceUrl(eventId) {
  return `${API_BASE_URL}/api/evidence/${eventId}`
}

/** Upload video to backend for YOLO object tracking pipeline */
export async function uploadVideo(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(percentCompleted)
      }
    },
    timeout: 300000,
  })
}

export default api
