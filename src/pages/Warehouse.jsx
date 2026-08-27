import React from 'react'
import { inventory } from '../data/inventory'

function WarehouseCard({name,cap}){
  return (
    <div className="card">
      <h3>{name}</h3>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div className="small muted">Capacity</div>
        <div style={{fontWeight:700}}>{cap}</div>
      </div>
      <div style={{marginTop:10}} className="progress"><i style={{width:cap}}></i></div>
    </div>
  )
}

export default function Warehouse(){
  return (
    <div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,marginBottom:14}}>
        <WarehouseCard name="Sydney Warehouse" cap="82%" />
        <WarehouseCard name="Melbourne Warehouse" cap="64%" />
        <WarehouseCard name="Brisbane Warehouse" cap="47%" />
      </div>

      <div style={{display:'flex',gap:12,marginBottom:12}}>
        <button className="card">Inventory</button>
        <button className="card">Receiving</button>
        <button className="card">Picking</button>
        <button className="card">Packing</button>
      </div>

      <div className="card">
        <h3>Inventory</h3>
        <table className="table">
          <thead><tr><th>Product ID</th><th>Product</th><th>Category</th><th>Quantity</th><th>Reserved</th><th>Warehouse</th><th>Location</th><th>Status</th></tr></thead>
          <tbody>
            {inventory.map(i=> (
              <tr key={i.pid}><td>{i.pid}</td><td>{i.name}</td><td>{i.category}</td><td>{i.qty}</td><td>{i.reserved}</td><td>{i.warehouse}</td><td>{i.location}</td><td><span className={`badge ${i.status==='In Stock'?'delivered': i.status==='Low Stock'?'processing':'cancelled'}`}>{i.status}</span></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
