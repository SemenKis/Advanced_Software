import React from 'react'

const alerts = [
  {id:1, type:'Low inventory', desc:'P-1003 low stock at Brisbane'},
  {id:2, type:'Shipment delayed', desc:'SHP-003 delayed arriving to Sydney'},
  {id:3, type:'Warehouse capacity', desc:'Sydney Warehouse at 82% capacity'},
  {id:4, type:'Vehicle maintenance', desc:'TRK-03 requires service'}
]

export default function AlertsPanel(){
  return (
    <div className="card">
      <h3>Alerts</h3>
      <ul style={{margin:0,padding:0,listStyle:'none',marginTop:10}}>
        {alerts.map(a=> (
          <li key={a.id} style={{padding:'8px 0',borderBottom:'1px solid rgba(255,255,255,0.02)'}}>
            <div style={{fontWeight:700}}>{a.type}</div>
            <div className="small muted">{a.desc}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}
