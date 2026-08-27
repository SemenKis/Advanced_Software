import React from 'react'

export default function RecentOrders({orders}){
  return (
    <div className="card">
      <h3>Recent Orders</h3>
      <table className="table">
        <thead><tr><th>Order ID</th><th>Customer</th><th>Date</th><th>Total</th><th>Status</th></tr></thead>
        <tbody>
          {orders.slice(0,6).map(o=> (
            <tr key={o.id}>
              <td>{o.id}</td>
              <td>{o.customer}</td>
              <td className="small muted">{o.date}</td>
              <td>{o.total}</td>
              <td><span className={`badge ${o.status.toLowerCase()==='delivered'? 'delivered': o.status.toLowerCase()==='cancelled' ? 'cancelled' : 'processing'}`}>{o.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
