import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Documents from './pages/Documents'
import AgentConfig from './pages/AgentConfig'
import Conversations from './pages/Conversations'
import Users from './pages/Users'
import AuditLog from './pages/AuditLog'

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex' }}>
      <Sidebar />
      <main style={{ marginLeft: 220, flex: 1, padding: 28, minHeight: '100vh' }}>
        {children}
      </main>
    </div>
  )
}

function Protected({ children, superadminOnly = false }: { children: React.ReactNode; superadminOnly?: boolean }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (superadminOnly && user.role !== 'superadmin') return <Navigate to="/documents" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/documents" /> : <Login />} />
      <Route path="/documents" element={<Protected><Layout><Documents /></Layout></Protected>} />
      <Route path="/config" element={<Protected><Layout><AgentConfig /></Layout></Protected>} />
      <Route path="/conversations" element={<Protected><Layout><Conversations /></Layout></Protected>} />
      <Route path="/users" element={<Protected superadminOnly><Layout><Users /></Layout></Protected>} />
      <Route path="/audit" element={<Protected superadminOnly><Layout><AuditLog /></Layout></Protected>} />
      <Route path="*" element={<Navigate to={user ? '/documents' : '/login'} />} />
    </Routes>
  )
}

export default function App() {
  return <AuthProvider><AppRoutes /></AuthProvider>
}
