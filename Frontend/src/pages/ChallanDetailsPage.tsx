import { Link, useParams } from 'react-router-dom'
import { AppShell } from '@/app/layout/AppShell'
import { useChallanDetailsQuery } from '@/modules/challans/hooks/useChallanDetailsQuery'
import { DataState } from '@/shared/components/DataState'
import { endpoints } from '@/shared/api/endpoints'
import { env } from '@/shared/config/env'

export function ChallanDetailsPage() {
  const { id } = useParams()
  const query = useChallanDetailsQuery(id)

  return (
    <AppShell>
      <div className="row" style={{ marginBottom: '0.5rem' }}>
        <Link to="/challans" className="btn-ghost">← Back to e-Challans</Link>
      </div>

      <section className="section-card">
        <div className="section-header">
          <span className="section-icon">🧾</span>
          <h2 style={{ marginBottom: 0 }}>e-Challan Details</h2>
          {query.data ? (
            <a
              href={`${env.VITE_API_BASE_URL}${endpoints.challanPdf(query.data.challan_id)}`}
              className="btn-primary"
              style={{ marginLeft: 'auto' }}
            >
              Download PDF
            </a>
          ) : null}
        </div>

        <DataState
          isLoading={query.isLoading}
          error={query.error}
          isEmpty={!query.data}
          emptyMessage="Challan record not found."
        >
          {query.data ? (
            <div className="detail-grid">
              <section className="section-card" style={{ margin: 0 }}>
                <div className="section-header">
                  <span className="section-icon">📋</span>
                  <h3>Challan Metadata</h3>
                </div>

                <div className="detail-list">
                  <div className="detail-row"><span className="detail-label">Challan ID</span><span className="font-mono">{query.data.challan_id}</span></div>
                  <div className="detail-row"><span className="detail-label">Violation ID</span><span className="font-mono">{query.data.violation_id || 'N/A'}</span></div>
                  <div className="detail-row"><span className="detail-label">Plate Number</span><span>{query.data.plate_number || 'N/A'}</span></div>
                  <div className="detail-row"><span className="detail-label">Vehicle Type</span><span>{query.data.vehicle_type}</span></div>
                  <div className="detail-row"><span className="detail-label">Vehicle Color</span><span>{query.data.vehicle_color}</span></div>
                  <div className="detail-row"><span className="detail-label">Violation Type</span><span>{query.data.violation_type}</span></div>
                  <div className="detail-row"><span className="detail-label">Fine Amount</span><span>₹{query.data.fine_amount}</span></div>
                  <div className="detail-row"><span className="detail-label">Status</span><span>{query.data.status}</span></div>
                  <div className="detail-row"><span className="detail-label">Timestamp</span><span>{query.data.timestamp ? new Date(query.data.timestamp).toLocaleString() : 'N/A'}</span></div>
                  <div className="detail-row"><span className="detail-label">Camera</span><span>{query.data.camera_id || 'N/A'}</span></div>
                  <div className="detail-row"><span className="detail-label">Location</span><span>{query.data.location_name || 'N/A'}</span></div>
                </div>

                {query.data.violation_id ? (
                  <div className="divider" />
                ) : null}

                {query.data.violation_id ? (
                  <Link to={`/violations/${query.data.violation_id}`} className="btn-ghost" style={{ display: 'inline-block' }}>
                    Open Source Violation
                  </Link>
                ) : null}
              </section>

              <section className="section-card" style={{ margin: 0 }}>
                <div className="section-header">
                  <span className="section-icon">📷</span>
                  <h3>Violation Image</h3>
                </div>
                <div className="camera-preview-shell">
                  {query.data.image_url ? (
                    <img
                      src={`${env.VITE_API_BASE_URL}${endpoints.challanImage(query.data.challan_id)}`}
                      alt={`Challan evidence ${query.data.challan_id}`}
                      className="camera-preview-image"
                    />
                  ) : (
                    <p className="text-sm muted" style={{ textAlign: 'center', padding: '1rem' }}>
                      No violation image available for this challan.
                    </p>
                  )}
                </div>
              </section>
            </div>
          ) : null}
        </DataState>
      </section>
    </AppShell>
  )
}
