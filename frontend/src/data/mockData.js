// ─── Tracked Persons (Current Frame) ─────────────────────────────
export const trackedPersons = [
  {
    id: 1,
    trackId: '#TRK-1089',
    label: 'Person #1',
    behaviour: 'Walking',
    status: 'Normal',
    speed: '1.2 m/s',
    dwell: '0m 45s',
    zone: 'Aisle 3',
    confidence: 98.4,
    boundingBox: { top: '28%', left: '16%', width: '12%', height: '46%' },
  },
  {
    id: 2,
    trackId: '#TRK-1091',
    label: 'Person #2',
    behaviour: 'Walking',
    status: 'Normal',
    speed: '0.9 m/s',
    dwell: '1m 12s',
    zone: 'Loading Bay',
    confidence: 94.1,
    boundingBox: { top: '32%', left: '42%', width: '8%', height: '34%' },
  },
  {
    id: 3,
    trackId: '#TRK-1093',
    label: 'Person #3',
    behaviour: 'Loitering',
    status: 'Abnormal',
    speed: '0.0 m/s',
    dwell: '12s',
    zone: 'Restricted Bay 4',
    confidence: 99.2,
    boundingBox: { top: '22%', left: '68%', width: '15%', height: '58%' },
  },
  {
    id: 4,
    trackId: '#TRK-1096',
    label: 'Person #4',
    behaviour: 'Walking',
    status: 'Normal',
    speed: '1.4 m/s',
    dwell: '0m 22s',
    zone: 'Gate A',
    confidence: 96.5,
    boundingBox: { top: '35%', left: '55%', width: '9%', height: '38%' },
  },
]

// ─── Behaviour Events (Audit Log) ────────────────────────────────
export const behaviourEvents = [
  {
    id: 1,
    timestamp: '00:01:32',
    gmtTime: '14:38:48 GMT',
    camera: 'CAM 07',
    zone: 'Sector C (Bay 04)',
    personId: 3,
    personLabel: 'Person #3',
    trackId: '#TRK-1093',
    behaviour: 'Loitering / Dwell > 10s',
    dwell: '12s',
    classification: 'Abnormal',
    confidence: 99.2,
  },
  {
    id: 2,
    timestamp: '00:02:15',
    gmtTime: '14:39:31 GMT',
    camera: 'CAM 07',
    zone: 'Aisle 3 West',
    personId: 1,
    personLabel: 'Person #1',
    trackId: '#TRK-1090',
    behaviour: 'Walking in transit',
    dwell: '45s',
    classification: 'Normal',
    confidence: 98.4,
  },
  {
    id: 3,
    timestamp: '00:00:25',
    gmtTime: '14:37:41 GMT',
    camera: 'CAM 07',
    zone: 'Staging Zone 1',
    personId: 2,
    personLabel: 'Person #2',
    trackId: '#TRK-1091',
    behaviour: 'Material handling',
    dwell: '1m 12s',
    classification: 'Normal',
    confidence: 94.1,
  },
  {
    id: 4,
    timestamp: '00:00:54',
    gmtTime: '14:38:10 GMT',
    camera: 'CAM 03',
    zone: 'Gate 2 Perimeter',
    personId: 4,
    personLabel: 'Person #4',
    trackId: '#TRK-1094',
    behaviour: 'Restricted boundary breach',
    dwell: '8s',
    classification: 'Abnormal',
    confidence: 99.7,
  },
  {
    id: 5,
    timestamp: '00:01:08',
    gmtTime: '14:38:24 GMT',
    camera: 'CAM 07',
    zone: 'Loading Dock B',
    personId: 5,
    personLabel: 'Person #5',
    trackId: '#TRK-1098',
    behaviour: 'Walking / Uniform pacing',
    dwell: '22s',
    classification: 'Normal',
    confidence: 96.5,
  },
  {
    id: 6,
    timestamp: '00:01:48',
    gmtTime: '14:39:04 GMT',
    camera: 'CAM 07',
    zone: 'Pallet Rack A9',
    personId: 2,
    personLabel: 'Person #2',
    trackId: '#TRK-1091',
    behaviour: 'Equipment inspection',
    dwell: '34s',
    classification: 'Normal',
    confidence: 97.3,
  },
  {
    id: 7,
    timestamp: '00:02:30',
    gmtTime: '14:39:46 GMT',
    camera: 'CAM 07',
    zone: 'Exit Corridor N',
    personId: 1,
    personLabel: 'Person #1',
    trackId: '#TRK-1090',
    behaviour: 'Walking / Transit Out',
    dwell: '19s',
    classification: 'Normal',
    confidence: 99.1,
  },
]

// ─── Dashboard KPI Statistics ────────────────────────────────────
export const dashboardStats = {
  peopleDetected: { value: 1248, trend: '+14%', description: 'Active multi-person tracking engine', baseline: 'Baseline: 1,094/day' },
  activeTracks: { value: 18, badge: 'LIVE LOCK', description: 'Across 12 connected CCTV cameras', detail: 'DeepSORT Kalman' },
  normalBehaviours: { value: 1232, percentage: '98.7%', description: 'Standard pattern baseline match', detail: 'Zone Compliance' },
  abnormalAlerts: { value: 16, badge: 'Attention Req.', description: 'Immediate operational review queue', detail: '3 Unresolved' },
}

// ─── Recent Analysis Sessions ────────────────────────────────────
export const recentSessions = [
  { filename: 'warehouse_floorA_shift1.mp4', camera: 'CAM 07 - Warehouse Floor A', duration: '04:15', timeAgo: '12m ago', resolution: '1080P', alerts: 1, status: 'flagged' },
  { filename: 'loading_dock_south_gate.mp4', camera: 'CAM 03 - Gate 2', duration: '12:40', timeAgo: '38m ago', resolution: '1080P', alerts: 0, status: 'normal' },
  { filename: 'restricted_vault_corridor.mp4', camera: 'CAM 11 - Vault B', duration: '08:22', timeAgo: '1h ago', resolution: '4K UHD', alerts: 3, status: 'flagged' },
  { filename: 'assembly_line_bay3.mp4', camera: 'CAM 09 - Line 3', duration: '15:00', timeAgo: '2h ago', resolution: '1080P', alerts: 0, status: 'normal' },
]

// ─── Security Alerts ─────────────────────────────────────────────
export const securityAlerts = [
  {
    id: 1,
    personLabel: 'Person #3',
    camera: 'CAM 07',
    title: 'Prolonged Loitering in Restricted Bay 4',
    anomalyScore: 99.2,
    dwell: '12s',
    timestamp: '14:38:48',
    status: 'ACTION REQUIRED',
    statusColor: 'error',
  },
  {
    id: 2,
    personLabel: 'Person #8',
    camera: 'CAM 03',
    title: 'Unauthorized Directional Flow (Counter-flow)',
    anomalyScore: 94.5,
    dwell: '8s',
    timestamp: '13:52:10',
    status: 'UNDER REVIEW',
    statusColor: 'secondary',
  },
  {
    id: 3,
    personLabel: 'Person #14',
    camera: 'CAM 11',
    title: 'Rapid Movement / Running in Staging Area',
    anomalyScore: 91.0,
    dwell: '18s',
    timestamp: '12:15:04',
    status: 'RESOLVED',
    statusColor: 'tertiary',
  },
]

// ─── Behaviour Distribution (for Charts) ─────────────────────────
export const behaviourDistribution = [
  { name: 'Transit Walking', value: 65, count: 3133, color: '#4cd7f6' },
  { name: 'Standing / Stationary', value: 25, count: 1205, color: '#8c909f' },
  { name: 'Loitering / Idle', value: 7, count: 337, color: '#ffb4ab' },
  { name: 'Rapid / Running', value: 3, count: 145, color: '#4d8eff' },
]

// ─── Hourly Timeline Data ────────────────────────────────────────
export const hourlyTimeline = [
  { hour: '08h', normal: 42, anomaly: 4 },
  { hour: '09h', normal: 80, anomaly: 2 },
  { hour: '10h', normal: 110, anomaly: 6 },
  { hour: '11h', normal: 135, anomaly: 4 },
  { hour: '12h', normal: 95, anomaly: 8 },
  { hour: '13h', normal: 105, anomaly: 5 },
  { hour: '14h', normal: 120, anomaly: 52 },
  { hour: '15h', normal: 140, anomaly: 16 },
  { hour: '16h', normal: 125, anomaly: 6 },
  { hour: '17h', normal: 70, anomaly: 4 },
  { hour: '18h', normal: 38, anomaly: 2 },
]

// ─── Zone Risk Data ──────────────────────────────────────────────
export const zoneRiskData = [
  { zone: 'Restricted Bay 4', anomalyRate: 18.2, status: 'ABNORMAL', description: 'High Anomaly Rate • Unapproved Loitering (34 instances)', icon: 'error' },
  { zone: 'Gate 2 Loading Dock', anomalyRate: 4.3, status: 'MONITORED', description: 'Moderate Anomaly • Transient congestion in transit lane', icon: 'secondary' },
  { zone: 'Main Forklift Aisle', anomalyRate: 1.1, status: 'OPTIMAL', description: 'Low Anomaly Rate • Standard flow conforming to speed envelope', icon: 'tertiary' },
]

// ─── Model Performance Metrics ───────────────────────────────────
export const modelMetrics = [
  { label: 'Tracking Precision (Multi-Person MOTA)', value: 99.4, description: 'Evaluated across 1,420 concurrent bounding boxes under low-lux conditions.', color: 'tertiary' },
  { label: 'False Positive Rate (FPR)', value: 0.6, description: 'Suppressed shadows and vehicle headlights using spatio-temporal filtering.', color: 'secondary' },
  { label: 'DeepSORT Track Continuity (ID Switch Resistance)', value: 99.1, description: 'Maintains persistent subject identity through partial physical occlusions.', color: 'primary' },
]
