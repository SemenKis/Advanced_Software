import React from 'react'
import ShipmentTable from '../components/transportation/ShipmentTable'
import VehicleCard from '../components/transportation/VehicleCard'
import { shipments } from '../data/shipments'
import { vehicles } from '../data/vehicles'

export default function Transportation(){
  const active = shipments.map(s=> ({...s, driver: s.id==='SHP-001'? 'James Smith': s.id==='SHP-005'? 'Carlos Vega': 'TBD', vehicle: s.id==='SHP-001'? 'TRK-04':'TRK-02'}))
  return (
    <div>
      <div className="kpi-grid">
        <div className="card"><h3>Active Shipments</h3><div className="stat-value">{active.length}</div></div>
        <div className="card"><h3>Available Vehicles</h3><div className="stat-value">{vehicles.filter(v=>v.status==='Available').length}</div></div>
        <div className="card"><h3>Drivers on Delivery</h3><div className="stat-value">{2}</div></div>
        <div className="card"><h3>Delayed Shipments</h3><div className="stat-value">{shipments.filter(s=>s.status==='Delayed').length}</div></div>
      </div>

      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',margin:'12px 0'}}>
        <h3>Transportation</h3>
        <button className="card">Create Shipment</button>
      </div>

      <ShipmentTable shipments={active} />

      <h3 style={{marginTop:16}}>Fleet Overview</h3>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:12}}>
        {vehicles.map(v=> <VehicleCard key={v.vid} v={v} />)}
      </div>

      <h3 style={{marginTop:16}}>Route / Tracking (Demo)</h3>
      <div className="route-panel card">
        <div>
          <div style={{fontWeight:700}}>SHP-001</div>
          <div className="small muted">Sydney → Melbourne</div>
        </div>
        <div style={{flex:1,textAlign:'center'}}>
          <div className="small muted">Origin</div>
          <div style={{margin:'8px 0',fontWeight:700}}>●—————◉—————○</div>
          <div className="small muted">Destination</div>
        </div>
        <div style={{textAlign:'right'}}>
          <div className="small muted">Current</div>
          <div style={{fontWeight:700}}>En Route (50%)</div>
        </div>
      </div>
    </div>
  )
}
