import React, { useEffect, useState } from 'react'
import { getAuditLog } from '../api/admin'

interface Log { id: string; user_id: string|null; action: string; details: string|null; ip: string|null; created_at: string }

export default function AuditLog() {
  const [logs, setLogs] = useState<Log[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { getAuditLog().then(r=>{setLogs(r.data);setLoading(false)}) }, [])

  const actionColor: Record<string,string> = {
    login: 'var(--success)', logout: 'var(--text-muted)',
    upload_document: 'var(--accent)', delete_document: 'var(--danger)',
    create_user: '#a855f7', toggle_user: 'var(--warning)',
    update_config: 'var(--accent)', change_password: 'var(--warning)',
  }

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:600,marginBottom:20}}>Audit Log</h1>
      <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,overflow:'hidden'}}>
        {loading ? <div style={{padding:24,color:'var(--text-muted)'}}>Loading...</div> : (
          <table style={{width:'100%',borderCollapse:'collapse'}}>
            <thead>
              <tr style={{borderBottom:'1px solid var(--border)'}}>
                {['Time','Action','Details','IP'].map(h=>(
                  <th key={h} style={{padding:'10px 14px',textAlign:'left',fontSize:11,color:'var(--text-muted)',fontWeight:500,textTransform:'uppercase'}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.map(l=>(
                <tr key={l.id} style={{borderBottom:'1px solid var(--border)'}}>
                  <td style={{padding:'8px 14px',fontSize:12,color:'var(--text-muted)',whiteSpace:'nowrap'}}>{new Date(l.created_at).toLocaleString()}</td>
                  <td style={{padding:'8px 14px'}}>
                    <span style={{fontSize:12,fontWeight:500,color:actionColor[l.action]||'var(--text)'}}>{l.action}</span>
                  </td>
                  <td style={{padding:'8px 14px',fontSize:12,color:'var(--text-muted)',maxWidth:320,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{l.details||'—'}</td>
                  <td style={{padding:'8px 14px',fontSize:12,color:'var(--text-muted)',fontFamily:'monospace'}}>{l.ip||'—'}</td>
                </tr>
              ))}
              {!logs.length && <tr><td colSpan={4} style={{padding:24,textAlign:'center',color:'var(--text-muted)'}}>No logs yet</td></tr>}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
