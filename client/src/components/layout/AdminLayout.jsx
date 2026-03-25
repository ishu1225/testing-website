import { useState } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { clearAdminAuth, getAdminAuth } from '../../utils/adminAuth'
import Toast from '../Toast'
import { api } from '../../services/api'

function AdminLayout() {
  const navigate = useNavigate()
  const admin = getAdminAuth()?.admin
  const [toast, setToast] = useState({ message: '', type: 'success' })

  const onLogout = () => {
    clearAdminAuth()
    navigate('/admin/login')
  }

  const onDeleteAccount = async () => {
    const ok = window.confirm('Delete your admin account and all your tests/results? This cannot be undone.')
    if (!ok) return

    try {
      await api.deleteAdminAccount()
      clearAdminAuth()
      setToast({ message: 'Account deleted', type: 'success' })
      navigate('/admin/register')
    } catch (err) {
      setToast({ message: err.message || 'Could not delete account', type: 'error' })
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 to-slate-200">
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Link to="/admin" className="text-lg font-bold text-slate-900">
              English Test Admin
            </Link>
            <Link
              to="/admin/create-test"
              className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white transition hover:bg-indigo-700"
            >
              New Test
            </Link>
            {admin?.userId === 'ISHU' ? (
              <Link
                to="/admin/master"
                className="rounded bg-slate-900 px-3 py-1.5 text-sm text-white transition hover:bg-slate-800"
              >
                Master Admin
              </Link>
            ) : null}
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">{admin?.userId}</span>
            <button
              onClick={onLogout}
              className="rounded bg-slate-800 px-3 py-1.5 text-white transition hover:bg-slate-900"
            >
              Logout
            </button>
            <button
              onClick={onDeleteAccount}
              className="rounded bg-rose-600 px-3 py-1.5 text-white transition hover:bg-rose-700"
            >
              Delete Account
            </button>
          </div>
        </div>
      </header>
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <Outlet />
    </div>
  )
}

export default AdminLayout
