import React from 'react'

export default function ShipmentTable({shipments}){
  return (
    <div className="card">
      <h3>Active Shipments</h3>
      <table className="table">
        <thead><tr><th>ID</th><th>Origin</th><th>Destination</th><th>Driver</th><th>Vehicle</th><th>Departure</th><th>ETA</th><th>Status</th></tr></thead>
        <tbody>
          {shipments.map(s=> (
            <tr key={s.id}><td>{s.id}</td><td>{s.origin}</td><td>{s.dest}</td><td>{s.driver||'—'}</td><td>{s.vehicle||'—'}</td><td className="small muted">{s.departure||'—'}</td><td className="small muted">{s.eta}</td><td><span className={`badge ${s.status.toLowerCase()==='delayed'?'cancelled': s.status.toLowerCase()==='delivered'?'delivered':'processing'}`}>{s.status}</span></td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
