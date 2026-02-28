import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/config', label: 'Agent Config', icon: '⚙️' },
  { path: '/conversations', label: 'Conversations', icon: '💬' },
]
const adminItems = [
  { path: '/users', label: 'Users', icon: '👥' },
  { path: '/audit', label: 'Audit Log', icon: '📋' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  return (
    <aside style={{width:220,background:'var(--bg-card)',borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column',height:'100vh',position:'fixed',left:0,top:0}}>
      <div style={{padding:'20px 16px',borderBottom:'1px solid var(--border)'}}>
        <span style={{fontWeight:600,fontSize:15}}>Dev<span style={{color:'var(--accent)'}}>Punks</span></span>
        <div style={{fontSize:11,color:'var(--text-muted)',marginTop:2}}>Admin Panel</div>
      </div>
      <nav style={{flex:1,padding:'12px 8px',overflowY:'auto'}}>
        {navItems.map(item => (
          <NavLink key={item.path} to={item.path} style={({isActive}) => ({
            display:'flex',alignItems:'center',gap:10,padding:'9px 12px',borderRadius:6,marginBottom:2,
            color: isActive ? 'var(--text)' : 'var(--text-muted)',
            background: isActive ? 'var(--bg-hover)' : 'transparent',
            textDecoration:'none',fontSize:13,
          })}>
            <span>{item.icon}</span>{item.label}
          </NavLink>
        ))}
        {user?.role === 'superadmin' && (
          <>
            <div style={{fontSize:10,color:'var(--text-dim)',padding:'12px 12px 4px',textTransform:'uppercase',letterSpacing:'0.08em'}}>SuperAdmin</div>
            {adminItems.map(item => (
              <NavLink key={item.path} to={item.path} style={({isActive}) => ({
                display:'flex',alignItems:'center',gap:10,padding:'9px 12px',borderRadius:6,marginBottom:2,
                color: isActive ? 'var(--text)' : 'var(--text-muted)',
                background: isActive ? 'var(--bg-hover)' : 'transparent',
                textDecoration:'none',fontSize:13,
              })}>
                <span>{item.icon}</span>{item.label}
              </NavLink>
            ))}
          </>
        )}
      </nav>
      <div style={{padding:'12px 16px',borderTop:'1px solid var(--border)'}}>
        <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:4,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{user?.email}</div>
        <span className={`badge badge-${user?.role}`}>{user?.role}</span>
        <button onClick={logout} style={{marginTop:8,width:'100%',background:'transparent',color:'var(--text-muted)',border:'1px solid var(--border)',fontSize:12,padding:'6px 0'}}>
          Sign out
        </button>
      </div>
    </aside>
  )
}
