import React from 'react'
import StatCard from '../components/dashboard/StatCard'
import RecentOrders from '../components/dashboard/RecentOrders'
import ActiveShipments from '../components/dashboard/ActiveShipments'
import AlertsPanel from '../components/dashboard/AlertsPanel'
import { orders } from '../data/orders'
import { shipments } from '../data/shipments'

export default function Dashboard(){
  return (
    <div>
      <div className="kpi-grid">
        <StatCard title="Products in Stock" value="1,248" />
        <StatCard title="Active Orders" value="37" />
        <StatCard title="Shipments in Transit" value="18" />
        <StatCard title="Delayed Shipments" value="3" />
      </div>

      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:16}}>
        <div>
          <RecentOrders orders={orders} />
          <div className="charts">
            <div className="card">
              <h3>Orders per Week</h3>
              <svg width="100%" height="90"><rect x="5" y="20" width="40" height="60" fill="#06b6d4" rx="4"/><rect x="55" y="40" width="40" height="40" fill="#0ea5a4" rx="4"/><rect x="105" y="10" width="40" height="70" fill="#38bdf8" rx="4"/></svg>
            </div>
            <div className="card">
              <h3>Delivery Performance</h3>
              <svg width="100%" height="90"><circle cx="40" cy="45" r="28" fill="#073047" stroke="#06b6d4" strokeWidth="10"/></svg>
            </div>
          </div>
        </div>
        <div>
          <ActiveShipments shipments={shipments} />
          <AlertsPanel />
        </div>
      </div>
    </div>
  )
}
