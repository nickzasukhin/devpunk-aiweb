import React, { useEffect, useState } from 'react'
import { getVisitors, getVisitorConversations } from '../api/admin'

interface Visitor { id: string; anonymous_id: string; first_seen_at: string; last_seen_at: string; metadata: any; conversation_count: number }
interface Msg { role: string; content: string; timestamp: string }
interface Conv { id: string; channel: string; agent: string; started_at: string; ended_at: string|null; audio_url: string|null; messages: Msg[] }

export default function Conversations() {
  const [visitors, setVisitors] = useState<Visitor[]>([])
  const [selected, setSelected] = useState<Visitor|null>(null)
  const [convs, setConvs] = useState<Conv[]>([])
  const [activeConv, setActiveConv] = useState<Conv|null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => { getVisitors().then(r=>{setVisitors(r.data);setLoading(false)}) }, [])

  const selectVisitor = async (v: Visitor) => {
    setSelected(v); setActiveConv(null)
    const r = await getVisitorConversations(v.id)
    setConvs(r.data.conversations)
  }

  return (
    <div style={{display:'grid',gridTemplateColumns:'280px 1fr',gap:16,height:'calc(100vh - 80px)'}}>
      {/* Visitor list */}
      <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,overflow:'hidden',display:'flex',flexDirection:'column'}}>
        <div style={{padding:'12px 14px',borderBottom:'1px solid var(--border)',fontSize:13,fontWeight:500}}>Visitors ({visitors.length})</div>
        <div className="scrollable" style={{flex:1}}>
          {loading ? <div style={{padding:16,color:'var(--text-muted)',fontSize:12}}>Loading...</div> : visitors.map(v=>(
            <div key={v.id} onClick={()=>selectVisitor(v)} style={{padding:'10px 14px',borderBottom:'1px solid var(--border)',cursor:'pointer',background:selected?.id===v.id?'var(--bg-hover)':'transparent',transition:'background 0.15s'}}>
              <div style={{fontSize:12,fontFamily:'monospace',color:'var(--text-muted)'}}>{v.anonymous_id.slice(0,16)}...</div>
              <div style={{display:'flex',gap:8,marginTop:4,alignItems:'center'}}>
                <span style={{fontSize:11,color:'var(--text-dim)'}}>{v.conversation_count} conv</span>
                {v.metadata?.country && <span style={{fontSize:11,color:'var(--text-dim)'}}>• {v.metadata.country}</span>}
                <span style={{fontSize:10,color:'var(--text-dim)',marginLeft:'auto'}}>{new Date(v.last_seen_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
          {!loading && !visitors.length && <div style={{padding:16,color:'var(--text-muted)',fontSize:12,textAlign:'center'}}>No visitors yet</div>}
        </div>
      </div>

      {/* Conversation area */}
      <div style={{display:'grid',gridTemplateColumns:'200px 1fr',gap:12,overflow:'hidden'}}>
        {/* Conv list */}
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,overflow:'hidden',display:'flex',flexDirection:'column'}}>
          <div style={{padding:'12px 14px',borderBottom:'1px solid var(--border)',fontSize:13,fontWeight:500}}>Conversations</div>
          <div className="scrollable" style={{flex:1}}>
            {!selected && <div style={{padding:16,color:'var(--text-muted)',fontSize:12}}>Select a visitor</div>}
            {convs.map(c=>(
              <div key={c.id} onClick={()=>setActiveConv(c)} style={{padding:'10px 14px',borderBottom:'1px solid var(--border)',cursor:'pointer',background:activeConv?.id===c.id?'var(--bg-hover)':'transparent'}}>
                <div style={{display:'flex',gap:6,marginBottom:4}}>
                  <span className={`badge badge-${c.channel}`}>{c.channel}</span>
                </div>
                <div style={{fontSize:11,color:'var(--text-dim)'}}>{new Date(c.started_at).toLocaleString()}</div>
                <div style={{fontSize:11,color:'var(--text-dim)'}}>{c.messages.length} messages</div>
              </div>
            ))}
          </div>
        </div>

        {/* Chat view */}
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,display:'flex',flexDirection:'column',overflow:'hidden'}}>
          {!activeConv ? (
            <div style={{display:'flex',alignItems:'center',justifyContent:'center',flex:1,color:'var(--text-muted)',fontSize:13}}>Select a conversation</div>
          ) : (
            <>
              <div style={{padding:'12px 16px',borderBottom:'1px solid var(--border)',display:'flex',gap:8,alignItems:'center'}}>
                <span className={`badge badge-${activeConv.channel}`}>{activeConv.channel}</span>
                <span style={{fontSize:12,color:'var(--text-muted)'}}>{new Date(activeConv.started_at).toLocaleString()}</span>
                {activeConv.audio_url && (
                  <audio controls style={{height:28,marginLeft:'auto'}}>
                    <source src={activeConv.audio_url} />
                  </audio>
                )}
              </div>
              <div className="scrollable" style={{flex:1,padding:16}}>
                {activeConv.messages.map((m,i)=>(
                  <div key={i} className={`chat-msg ${m.role}`}>
                    {m.role==='assistant' && <div className="chat-avatar">DP</div>}
                    <div className="chat-bubble">{m.content}</div>
                    {m.role==='user' && <div className="chat-avatar" style={{background:'var(--border)'}}>U</div>}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
