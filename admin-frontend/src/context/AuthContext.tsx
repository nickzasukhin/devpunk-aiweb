import React, { createContext, useContext, useState, useEffect } from 'react'
import { getMe } from '../api/auth'

interface User { id: string; email: string; role: string }
interface AuthCtx { user: User | null; setUser: (u: User | null) => void; logout: () => void }

const Ctx = createContext<AuthCtx>({ user: null, setUser: () => {}, logout: () => {} })

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { setLoading(false); return }
    getMe().then(r => setUser(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const logout = () => {
    localStorage.removeItem('access_token')
    setUser(null)
    window.location.href = '/login'
  }

  if (loading) return <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',color:'#888'}}>Loading...</div>
  return <Ctx.Provider value={{ user, setUser, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
