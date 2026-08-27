import React from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Warehouse from './pages/Warehouse'
import Transportation from './pages/Transportation'
import Suppliers from './pages/Suppliers'
import Reports from './pages/Reports'
import AI from './pages/AI'
import Settings from './pages/Settings'

export default function App(){
  const location = useLocation()
  return (
    <Layout title={location.pathname}>
      <Routes>
        <Route path='/' element={<Dashboard/>} />
        <Route path='/orders' element={<Orders/>} />
        <Route path='/warehouse' element={<Warehouse/>} />
        <Route path='/transportation' element={<Transportation/>} />
        <Route path='/suppliers' element={<Suppliers/>} />
        <Route path='/reports' element={<Reports/>} />
        <Route path='/ai' element={<AI/>} />
        <Route path='/settings' element={<Settings/>} />
      </Routes>
    </Layout>
  )
}
