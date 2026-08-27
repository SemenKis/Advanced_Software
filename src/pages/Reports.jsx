import React from 'react'

export default function Reports(){
  return (
    <div>
      <h3>Reports & Analytics</h3>
      <div className="kpi-grid" style={{marginTop:12}}>
        <div className="card"><h3>Monthly Orders</h3><div className="stat-value">1,842</div></div>
        <div className="card"><h3>Delivery Performance</h3><div className="stat-value">96%</div></div>
        <div className="card"><h3>Inventory Levels</h3><div className="stat-value">74%</div></div>
        <div className="card"><h3>Transportation Costs</h3><div className="stat-value">$42,300</div></div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginTop:12}}>
        <div className="card"><h3>Warehouse Utilisation</h3><div className="small muted">Sydney 82% • Melbourne 64% • Brisbane 47%</div></div>
        <div className="card"><h3>Supplier Performance</h3><div className="small muted">Top: TechSupply • Avg Lead Time: 9 days</div></div>
      </div>
    </div>
  )
}
