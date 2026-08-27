import React from 'react'

export default function Settings(){
  return (
    <div>
      <h3>Settings</h3>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginTop:12}}>
        <div className="card"><h4>Profile</h4><div className="small muted">Manage user profile and contact information (demo).</div></div>
        <div className="card"><h4>Notifications</h4><div className="small muted">Configure notification preferences (demo).</div></div>
        <div className="card"><h4>System Preferences</h4><div className="small muted">Timezone, regional settings, display options (demo).</div></div>
        <div className="card"><h4>AI Model Configuration</h4><div className="small muted">Select default model and demo settings for AI Assistant.</div></div>
      </div>
    </div>
  )
}
