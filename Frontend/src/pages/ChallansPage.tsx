import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '@/app/layout/AppShell'
import { useChallansQuery } from '@/modules/challans/hooks/useChallansQuery'
import { env } from '@/shared/config/env'
import { endpoints } from '@/shared/api/endpoints'
import { DataState } from '@/shared/components/DataState'

function toIsoDateBoundary(date: string, endOfDay = false) {
  if (!date) return undefined
  const suffix = endOfDay ? 'T23:59:59Z' : 'T00:00:00Z'
  return `${date}${suffix}`
}

export function ChallansPage() {
  const [challanId, setChallanId] = useState('')
  const [plateNumber, setPlateNumber] = useState('')
  const [violationType, setViolationType] = useState('')
  const [status, setStatus] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [cameraId, setCameraId] = useState('')
  const [limit, setLimit] = useState(25)

  const filters = useMemo(
    () => ({
      challan_id: challanId.trim() || undefined,
      plate_number: plateNumber.trim() || undefined,
      violation_type: violationType.trim() || undefined,
      status: status.trim() || undefined,
      from: toIsoDateBoundary(fromDate, false),
      to: toIsoDateBoundary(toDate, true),
      camera_id: cameraId.trim() || undefined,
      limit,
    }),
    [cameraId, challanId, fromDate, limit, plateNumber, status, toDate, violationType],
  )

  const query = useChallansQuery(filters)

  const exportUrl = useMemo(() => {
    const url = new URL(`${env.VITE_API_BASE_URL}${endpoints.challansBulkExport}`)
    const fromIso = toIsoDateBoundary(fromDate, false)
    const toIso = toIsoDateBoundary(toDate, true)
    if (fromIso) url.searchParams.set('from', fromIso)
    if (toIso) url.searchParams.set('to', toIso)
    if (cameraId.trim()) url.searchParams.set('camera_id', cameraId.trim())
    return url.toString()
  }, [cameraId, fromDate, toDate])

  return (
    <AppShell>
      <section className="section-card">
        <div className="section-header">
          <span className="section-icon">🧾</span>
          <h2 style={{ marginBottom: 0 }}>e-Challan Management</h2>
        </div>

        <p className="muted" style={{ marginBottom: '1rem' }}>
          Search generated challans, open details, and export bulk archives.
        </p>

        <div className="filter-bar">
          <label className="camera-lab-field">
            <span className="muted text-xs">Challan ID</span>
            <input type="text" value={challanId} onChange={(e) => setChallanId(e.target.value)} placeholder="CH-20260101-AB12CD34" />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">Plate Number</span>
            <input type="text" value={plateNumber} onChange={(e) => setPlateNumber(e.target.value)} placeholder="KA05AB1234" />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">Violation Type</span>
            <input type="text" value={violationType} onChange={(e) => setViolationType(e.target.value)} placeholder="FOOTPATH_ENCROACHMENT" />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">Status</span>
            <input type="text" value={status} onChange={(e) => setStatus(e.target.value)} placeholder="GENERATED" />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">From Date</span>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">To Date</span>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">Camera ID</span>
            <input
              type="text"
              placeholder="FP_CAM_001"
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
            />
          </label>
          <label className="camera-lab-field">
            <span className="muted text-xs">Limit</span>
            <input type="number" min={1} max={200} value={limit} onChange={(e) => setLimit(Number(e.target.value || 1))} />
          </label>
        </div>

        <div className="camera-config-actions">
          <a href={exportUrl} className="btn-primary">
            Download ZIP Export
          </a>
        </div>

        <div style={{ marginTop: '1rem' }}>
          <DataState
            isLoading={query.isLoading}
            error={query.error}
            isEmpty={(query.data?.items.length ?? 0) === 0}
            emptyMessage="No challans matched current filters."
          >
            <div className="table-wrapper" id="challans-table">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Challan ID</th>
                    <th>Plate</th>
                    <th>Vehicle</th>
                    <th>Violation</th>
                    <th>Time</th>
                    <th>Fine</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(query.data?.items ?? []).map((item) => (
                    <tr key={item.challan_id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{item.challan_id}</td>
                      <td><span className="pill">{item.plate_number || 'N/A'}</span></td>
                      <td>{item.vehicle_type || 'unknown'} / {item.vehicle_color || 'unknown'}</td>
                      <td>{item.violation_type}</td>
                      <td>{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'N/A'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>₹{item.fine_amount}</td>
                      <td>{item.status}</td>
                      <td>
                        <div className="row" style={{ gap: '0.5rem' }}>
                          <Link to={`/challans/${item.challan_id}`} className="btn-ghost" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                            View
                          </Link>
                          <a
                            href={`${env.VITE_API_BASE_URL}${endpoints.challanPdf(item.challan_id)}`}
                            className="btn-ghost"
                            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                          >
                            PDF
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DataState>
        </div>
      </section>
    </AppShell>
  )
}
