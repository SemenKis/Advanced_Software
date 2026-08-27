import React from 'react'
import ChatBox from '../components/ai/ChatBox'

export default function AI(){
  return (
    <div>
      <h3>AI Logistics Assistant</h3>
      <div className="card" style={{marginTop:12}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <div>
            <div style={{fontWeight:700}}>Qwen 2.5</div>
            <div className="small muted">Other models: Llama, DeepSeek (future)</div>
          </div>
          <div className="small muted">Architecture: Frontend → Backend/API → Ollama → LLM</div>
        </div>
      </div>

      <div style={{marginTop:12}}>
        <ChatBox />
      </div>
    </div>
  )
}
