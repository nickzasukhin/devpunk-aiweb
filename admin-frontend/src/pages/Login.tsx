import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setUser } = useAuth()
  const nav = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const r = await login(email, password)
      localStorage.setItem('access_token', r.data.access_token)
      setUser({ id: '', email, role: r.data.role })
      nav('/documents')
    } catch {
      setError('Invalid email or password')
    } finally { setLoading(false) }
  }

  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',minHeight:'100vh',background:'var(--bg)'}}>
      <div style={{width:360,background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:12,padding:32}}>
        <div style={{textAlign:'center',marginBottom:28}}>
          <div style={{fontSize:22,fontWeight:600}}>Dev<span style={{color:'var(--accent)'}}>Punks</span></div>
          <div style={{color:'var(--text-muted)',fontSize:13,marginTop:4}}>Admin Panel</div>
        </div>
        <form onSubmit={submit}>
          <label style={{display:'block',marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Email</div>
            <input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="admin@devpunks.io" required />
          </label>
          <label style={{display:'block',marginBottom:20}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Password</div>
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" required />
          </label>
          {error && <div style={{color:'var(--danger)',fontSize:12,marginBottom:12}}>{error}</div>}
          <button type="submit" className="btn-primary" style={{width:'100%',padding:'10px 0'}} disabled={loading}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
