import React from 'react'

export default function StatCard({title,value,delta}){
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="stat-value">{value}</div>
      {delta && <div className="small muted">{delta}</div>}
    </div>
  )
}
