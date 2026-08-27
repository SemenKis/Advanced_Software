import React from 'react'
import { Bell, Search, User } from 'lucide-react'

export default function Header({title}){
  return (
    <header className="header">
      <div className="flex" style={{alignItems:'center',gap:16}}>
        <h2 style={{margin:0}}>{title==='/'? 'Dashboard': title.replace('/','').replace(/\b\w/g,l=>l.toUpperCase())}</h2>
        <div className="search small">
          <Search size={14} />
          <input placeholder="Search orders, shipments, products..." style={{background:'transparent',border:0,color:'inherit',outline:'none'}} />
        </div>
      </div>
      <div className="flex" style={{alignItems:'center'}}>
        <Bell />
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <User />
          <div style={{textAlign:'right'}}>
            <div style={{fontSize:13,fontWeight:700}}>Alex Johnson</div>
            <div className="small muted">Operations</div>
          </div>
        </div>
      </div>
    </header>
  )
}
