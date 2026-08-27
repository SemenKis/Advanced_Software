import React from 'react'

export default function VehicleCard({v}){
  return (
    <div className="card">
      <h4 style={{margin:0}}>{v.vid} <span className="small muted">{v.type}</span></h4>
      <div className="small muted">Driver: {v.driver}</div>
      <div style={{marginTop:8}} className="small muted">Reg: {v.reg} • Capacity: {v.capacity}</div>
      <div style={{marginTop:8}}><span className={`badge ${v.status==='Available'? 'delivered': v.status==='In Use' ? 'processing' : 'cancelled'}`}>{v.status}</span></div>
    </div>
  )
}
