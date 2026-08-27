import React, {useState} from 'react'
import { orders as ordersData } from '../data/orders'

export default function Orders(){
  const [query,setQuery] = useState('')
  const [status,setStatus] = useState('All')
  const filtered = ordersData.filter(o=> (status==='All' || o.status===status) && (o.id.includes(query) || o.customer.toLowerCase().includes(query.toLowerCase())))
  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <h3>Orders</h3>
        <div className="flex">
          <input placeholder="Search orders" value={query} onChange={e=>setQuery(e.target.value)} className="search" />
          <select value={status} onChange={e=>setStatus(e.target.value)} style={{padding:8,borderRadius:8,background:'transparent',border:'1px solid rgba(255,255,255,0.03)'}}>
            <option>All</option>
            <option>Processing</option>
            <option>Dispatched</option>
            <option>Delivered</option>
            <option>Cancelled</option>
          </select>
          <button className="card" style={{cursor:'pointer'}}>New Order</button>
        </div>
      </div>
      <div className="card">
        <table className="table">
          <thead><tr><th>Order ID</th><th>Customer</th><th>Order Date</th><th>Destination</th><th>Items</th><th>Total</th><th>Status</th></tr></thead>
          <tbody>
            {filtered.map(o=> (
              <tr key={o.id}><td>{o.id}</td><td>{o.customer}</td><td className="small muted">{o.date}</td><td>{o.destination}</td><td>{o.items}</td><td>{o.total}</td><td><span className={`badge ${o.status.toLowerCase()==='delivered'?'delivered': o.status.toLowerCase()==='cancelled'?'cancelled':'processing'}`}>{o.status}</span></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
