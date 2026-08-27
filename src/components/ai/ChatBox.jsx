import React, {useState} from 'react'

const sample = [
  {from:'user', text:'Which shipments are currently delayed?'},
  {from:'ai', text:'There are currently 3 delayed shipments:\n\n• SHP-003 — Melbourne → Sydney\n• SHP-007 — Sydney → Brisbane\n• SHP-012 — Newcastle → Sydney'}
]

export default function ChatBox(){
  const [messages,setMessages] = useState(sample)
  const [input,setInput] = useState('')
  const send = ()=>{
    if(!input.trim()) return
    setMessages(m=>[...m,{from:'user',text:input},{from:'ai',text:'(Demo) This is a canned AI response — integration coming soon.'}])
    setInput('')
  }
  return (
    <div>
      <div className="card">
        <div className="small muted">AI Mode — Demo</div>
        <div style={{marginTop:12}}>
          {messages.map((m,i)=>(
            <div key={i} style={{marginBottom:10}}>
              <div style={{fontWeight:700}}>{m.from==='user'? 'User':'AI'}</div>
              <div className="small muted" style={{whiteSpace:'pre-wrap'}}>{m.text}</div>
            </div>
          ))}
        </div>
        <div style={{display:'flex',gap:8,marginTop:12}}>
          <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Type a message" style={{flex:1,padding:8,borderRadius:8,background:'transparent',border:'1px solid rgba(255,255,255,0.03)'}} />
          <button className="card" onClick={send}>Send</button>
        </div>
      </div>
    </div>
  )
}
