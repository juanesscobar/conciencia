import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import AuthGuard from './components/AuthGuard'
import { ModeProvider, Mode } from './contexts/ModeContext'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Tasks from './pages/Tasks'
import Reports from './pages/Reports'
import Agents from './pages/Agents'
import Workflows from './pages/Workflows'
import Approvals from './pages/Approvals'
import Context from './pages/Context'
import Governance from './pages/Governance'
import Traces from './pages/Traces'
import Costs from './pages/Costs'
import Audit from './pages/Audit'
import Leads from './pages/Leads'
import Settings from './pages/Settings'
import Login from './pages/Login'

function AppShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  // Default de modo por rol (spec §36): ceo/admin → operator, resto → client
  const defaultMode: Mode = user?.role === 'admin' || user?.role === 'ceo' ? 'operator' : 'client'
  return (
    <ModeProvider defaultMode={defaultMode}>
      <Layout>{children}</Layout>
    </ModeProvider>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  )
}

function App() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/projects" element={<ProtectedRoute><Projects /></ProtectedRoute>} />
      <Route path="/projects/:id" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />
      <Route path="/tasks" element={<ProtectedRoute><Tasks /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
      <Route path="/agents" element={<ProtectedRoute><Agents /></ProtectedRoute>} />
      <Route path="/workflows" element={<ProtectedRoute><Workflows /></ProtectedRoute>} />
      <Route path="/approvals" element={<ProtectedRoute><Approvals /></ProtectedRoute>} />
      <Route path="/context" element={<ProtectedRoute><Context /></ProtectedRoute>} />
      <Route path="/governance" element={<ProtectedRoute><Governance /></ProtectedRoute>} />
      <Route path="/traces" element={<ProtectedRoute><Traces /></ProtectedRoute>} />
      <Route path="/costs" element={<ProtectedRoute><Costs /></ProtectedRoute>} />
      <Route path="/audit" element={<ProtectedRoute><Audit /></ProtectedRoute>} />
      <Route path="/leads" element={<ProtectedRoute><Leads /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
