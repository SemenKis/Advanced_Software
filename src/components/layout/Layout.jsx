import React from 'react'
import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({children,title}){
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main">
        <Header title={title} />
        <div className="content">{children}</div>
      </div>
    </div>
  )
}
