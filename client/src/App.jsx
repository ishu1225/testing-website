import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from './components/layout/AdminLayout'
import ProtectedAdminRoute from './components/layout/ProtectedAdminRoute'
import AdminDashboardPage from './pages/AdminDashboardPage'
import CreateTestPage from './pages/CreateTestPage'
import ResultsPage from './pages/ResultsPage'
import StudentDetailsPage from './pages/StudentDetailsPage'
import TestPage from './pages/TestPage'
import AdminForgotPasswordPage from './pages/auth/AdminForgotPasswordPage'
import AdminChangePasswordPage from './pages/auth/AdminChangePasswordPage'
import AdminLoginPage from './pages/auth/AdminLoginPage'
import AdminRegisterPage from './pages/auth/AdminRegisterPage'
import AdminMasterPage from './pages/AdminMasterPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin/login" replace />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/admin/register" element={<AdminRegisterPage />} />
      <Route path="/admin/forgot-password" element={<AdminForgotPasswordPage />} />
      <Route element={<ProtectedAdminRoute />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/admin/create-test" element={<CreateTestPage />} />
          <Route path="/admin/change-password" element={<AdminChangePasswordPage />} />
          <Route path="/admin/master" element={<AdminMasterPage />} />
          <Route path="/admin/tests/:testId/results" element={<ResultsPage />} />
        </Route>
      </Route>
      <Route path="/test/:testId" element={<StudentDetailsPage />} />
      <Route path="/test/:testId/attempt" element={<TestPage />} />
    </Routes>
  )
}

export default App
