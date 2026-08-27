import React from 'react'

export default function ActiveShipments({shipments}){
  return (
    <div className="card">
      <h3>Active Shipments</h3>
      <table className="table">
        <thead><tr><th>Shipment</th><th>Route</th><th>ETA</th><th>Status</th></tr></thead>
        <tbody>
          {shipments.slice(0,6).map(s=> (
            <tr key={s.id}><td>{s.id}</td><td>{s.origin} → {s.dest}</td><td className="small muted">{s.eta}</td><td><span className={`badge ${s.status.toLowerCase()==='delayed'?'cancelled': s.status.toLowerCase()==='delivered'?'delivered': 'processing'}`}>{s.status}</span></td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
