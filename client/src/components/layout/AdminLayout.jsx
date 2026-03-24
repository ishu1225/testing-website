import { Link, Outlet, useNavigate } from 'react-router-dom'
import { clearAdminAuth, getAdminAuth } from '../../utils/adminAuth'

function AdminLayout() {
  const navigate = useNavigate()
  const admin = getAdminAuth()?.admin

  const onLogout = () => {
    clearAdminAuth()
    navigate('/admin/login')
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 to-slate-200">
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Link to="/admin" className="text-lg font-bold text-slate-900">
              English Test Admin
            </Link>
            <Link to="/admin/create-test" className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white">
              New Test
            </Link>
            <Link to="/admin/change-password" className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-800">
              Change Password
            </Link>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">{admin?.userId}</span>
            <button onClick={onLogout} className="rounded bg-slate-800 px-3 py-1.5 text-white">
              Logout
            </button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  )
}

export default AdminLayout
