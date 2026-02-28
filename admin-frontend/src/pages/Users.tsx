import React, { useEffect, useState } from 'react'
import { getUsers, createUser, toggleUser, resetPassword } from '../api/admin'

interface User { id: string; email: string; role: string; is_active: boolean; created_at: string; last_login: string|null }

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [form, setForm] = useState({email:'',password:''})
  const [pwReset, setPwReset] = useState<{id:string,pw:string}|null>(null)
  const [msg, setMsg] = useState('')

  const load = () => getUsers().then(r=>setUsers(r.data))
  useEffect(()=>{load()},[])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    try { await createUser(form.email,form.password); setForm({email:'',password:''}); load(); setMsg('User created ✓') }
    catch(e:any) { setMsg(e.response?.data?.detail||'Error') }
    setTimeout(()=>setMsg(''),3000)
  }

  return (
    <div>
      <h1 style={{fontSize:20,fontWeight:600,marginBottom:20}}>Users</h1>
      <div style={{display:'grid',gridTemplateColumns:'1fr 340px',gap:20}}>
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,overflow:'hidden'}}>
          <table style={{width:'100%',borderCollapse:'collapse'}}>
            <thead>
              <tr style={{borderBottom:'1px solid var(--border)'}}>
                {['Email','Role','Status','Last Login','Actions'].map(h=>(
                  <th key={h} style={{padding:'10px 14px',textAlign:'left',fontSize:11,color:'var(--text-muted)',fontWeight:500,textTransform:'uppercase'}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map(u=>(
                <tr key={u.id} style={{borderBottom:'1px solid var(--border)'}}>
                  <td style={{padding:'10px 14px',fontSize:13}}>{u.email}</td>
                  <td style={{padding:'10px 14px'}}><span className={`badge badge-${u.role}`}>{u.role}</span></td>
                  <td style={{padding:'10px 14px'}}><span className={`badge ${u.is_active?'badge-active':'badge-inactive'}`}>{u.is_active?'Active':'Inactive'}</span></td>
                  <td style={{padding:'10px 14px',fontSize:12,color:'var(--text-muted)'}}>{u.last_login?new Date(u.last_login).toLocaleString():'—'}</td>
                  <td style={{padding:'10px 14px'}}>
                    {u.role!=='superadmin' && (
                      <div style={{display:'flex',gap:6}}>
                        <button className="btn-secondary" style={{fontSize:11,padding:'4px 8px'}} onClick={()=>toggleUser(u.id).then(load)}>{u.is_active?'Deactivate':'Activate'}</button>
                        <button className="btn-secondary" style={{fontSize:11,padding:'4px 8px'}} onClick={()=>setPwReset({id:u.id,pw:''})}>Reset PW</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20,marginBottom:16}}>
            <h3 style={{fontWeight:600,marginBottom:14,fontSize:14}}>Create Admin</h3>
            <form onSubmit={create}>
              <label style={{display:'block',marginBottom:10}}>
                <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:4}}>Email</div>
                <input type="email" value={form.email} onChange={e=>setForm(p=>({...p,email:e.target.value}))} required />
              </label>
              <label style={{display:'block',marginBottom:14}}>
                <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:4}}>Password</div>
                <input type="password" value={form.password} onChange={e=>setForm(p=>({...p,password:e.target.value}))} required />
              </label>
              {msg && <div style={{fontSize:12,color:msg.includes('✓')?'var(--success)':'var(--danger)',marginBottom:8}}>{msg}</div>}
              <button type="submit" className="btn-primary" style={{width:'100%'}}>Create Admin</button>
            </form>
          </div>

          {pwReset && (
            <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20}}>
              <h3 style={{fontWeight:600,marginBottom:14,fontSize:14}}>Reset Password</h3>
              <input type="password" value={pwReset.pw} onChange={e=>setPwReset(p=>p?{...p,pw:e.target.value}:null)} placeholder="New password" style={{marginBottom:10}} />
              <div style={{display:'flex',gap:8}}>
                <button className="btn-primary" onClick={()=>resetPassword(pwReset.id,pwReset.pw).then(()=>setPwReset(null))}>Save</button>
                <button className="btn-secondary" onClick={()=>setPwReset(null)}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
