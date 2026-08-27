import React from 'react'
import { NavLink } from 'react-router-dom'
import { Home, Box, Map, Truck, Users, FileText, Cpu, Settings } from 'lucide-react'

const nav = [
  {to:'/', label:'Dashboard', icon:Home},
  {to:'/orders', label:'Orders', icon:Box},
  {to:'/warehouse', label:'Warehouse', icon:Map},
  {to:'/transportation', label:'Transportation', icon:Truck},
  {to:'/suppliers', label:'Suppliers', icon:Users},
  {to:'/reports', label:'Reports', icon:FileText},
  {to:'/ai', label:'AI Assistant', icon:Cpu},
  {to:'/settings', label:'Settings', icon:Settings}
]

export default function Sidebar(){
  return (
    <aside className="sidebar">
      <div className="logo">LogiFlow</div>
      <nav style={{marginTop:18}}>
        {nav.map(n=>{
          const Icon = n.icon
          return (
            <NavLink key={n.to} to={n.to} end className={({isActive})=>`nav-item ${isActive? 'active':''}`}>
              <Icon size={16} />
              <span>{n.label}</span>
            </NavLink>
          )
        })}
      </nav>
      <div className="sidebar-footer small muted">v0.1 • Demo UI</div>
    </aside>
  )
}
