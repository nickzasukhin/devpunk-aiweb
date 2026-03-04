import React, { useEffect, useState, useRef } from 'react'
import { getDocuments, uploadDocument, deleteDocument, reindexDocument } from '../api/admin'

interface Doc { id: string; filename: string; file_type: string; chunk_count: number; status: string; uploaded_at: string }

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = () => getDocuments().then(r => setDocs(r.data)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return
    setUploading(true)
    for (const f of Array.from(files)) {
      try { await uploadDocument(f) } catch(e: any) { alert(`Error: ${e.response?.data?.detail || e.message}`) }
    }
    await load()
    setUploading(false)
  }

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:600,marginBottom:20}}>Knowledge Base Documents</h1>

      <div
        onDragOver={e=>{e.preventDefault();setDragging(true)}}
        onDragLeave={()=>setDragging(false)}
        onDrop={e=>{e.preventDefault();setDragging(false);handleFiles(e.dataTransfer.files)}}
        onClick={()=>fileRef.current?.click()}
        style={{border:`2px dashed ${dragging?'var(--accent)':'var(--border)'}`,borderRadius:10,padding:32,textAlign:'center',cursor:'pointer',marginBottom:24,transition:'border-color 0.2s',background:dragging?'rgba(229,0,81,0.05)':'transparent'}}
      >
        <div style={{fontSize:28,marginBottom:8}}>📂</div>
        <div style={{color:'var(--text-muted)',fontSize:13}}>Drop files here or click to upload</div>
        <div style={{color:'var(--text-dim)',fontSize:11,marginTop:4}}>.md .txt .pdf .json</div>
        {uploading && <div style={{color:'var(--accent)',marginTop:8,fontSize:12}}>Uploading & indexing...</div>}
        <input ref={fileRef} type="file" multiple accept=".md,.txt,.pdf,.json" style={{display:'none'}} onChange={e=>handleFiles(e.target.files)} />
      </div>

      {loading ? <div style={{color:'var(--text-muted)'}}>Loading...</div> : (
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,overflow:'hidden'}}>
          <table style={{width:'100%',borderCollapse:'collapse'}}>
            <thead>
              <tr style={{borderBottom:'1px solid var(--border)'}}>
                {['Filename','Type','Chunks','Status','Uploaded','Actions'].map(h=>(
                  <th key={h} style={{padding:'10px 14px',textAlign:'left',fontSize:11,color:'var(--text-muted)',fontWeight:500,textTransform:'uppercase',letterSpacing:'0.06em'}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {docs.map(d=>(
                <tr key={d.id} style={{borderBottom:'1px solid var(--border)'}}>
                  <td style={{padding:'10px 14px',fontSize:13}}>{d.filename}</td>
                  <td style={{padding:'10px 14px'}}><span className="badge badge-text">{d.file_type}</span></td>
                  <td style={{padding:'10px 14px',fontSize:13,color:'var(--text-muted)'}}>{d.chunk_count}</td>
                  <td style={{padding:'10px 14px'}}><span className={`badge ${d.status==='indexed'?'badge-active':'badge-inactive'}`}>{d.status}</span></td>
                  <td style={{padding:'10px 14px',fontSize:12,color:'var(--text-muted)'}}>{new Date(d.uploaded_at).toLocaleDateString()}</td>
                  <td style={{padding:'10px 14px'}}>
                    <div style={{display:'flex',gap:6}}>
                      <button className="btn-secondary" style={{fontSize:11,padding:'4px 8px'}} onClick={()=>reindexDocument(d.id).then(load)}>Re-index</button>
                      <button className="btn-danger" style={{fontSize:11,padding:'4px 8px'}} onClick={()=>{if(confirm('Delete?'))deleteDocument(d.id).then(load)}}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!docs.length && <tr><td colSpan={6} style={{padding:24,textAlign:'center',color:'var(--text-muted)'}}>No documents yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
