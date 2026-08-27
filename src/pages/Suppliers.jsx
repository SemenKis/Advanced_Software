import React from 'react'
import { suppliers } from '../data/suppliers'

export default function Suppliers(){
  return (
    <div>
      <div className="kpi-grid">
        <div className="card"><h3>Total Suppliers</h3><div className="stat-value">{suppliers.length}</div></div>
        <div className="card"><h3>Active Suppliers</h3><div className="stat-value">{suppliers.filter(s=>s.status==='Active').length}</div></div>
        <div className="card"><h3>Pending POs</h3><div className="stat-value">{3}</div></div>
        <div className="card"><h3>Avg Lead Time</h3><div className="stat-value">9 days</div></div>
      </div>

      <div className="card">
        <h3>Suppliers</h3>
        <table className="table">
          <thead><tr><th>ID</th><th>Company</th><th>Products</th><th>Location</th><th>Contact</th><th>Lead Time</th><th>Status</th></tr></thead>
          <tbody>
            {suppliers.map(s=> (
              <tr key={s.id}><td>{s.id}</td><td>{s.company}</td><td>{s.products.join(', ')}</td><td>{s.location}</td><td>{s.contact}</td><td>{s.leadTime}</td><td><span className={`badge ${s.status.toLowerCase()==='active'?'delivered': s.status.toLowerCase()==='pending'?'processing':'cancelled'}`}>{s.status}</span></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
