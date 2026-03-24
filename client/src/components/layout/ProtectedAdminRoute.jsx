import { Navigate, Outlet } from 'react-router-dom'
import { getAdminToken } from '../../utils/adminAuth'

function ProtectedAdminRoute() {
  const token = getAdminToken()
  if (!token) return <Navigate to="/admin/login" replace />
  return <Outlet />
}

export default ProtectedAdminRoute
