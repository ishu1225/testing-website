import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Toast from '../../components/Toast'
import { api } from '../../services/api'
import { setAdminAuth } from '../../utils/adminAuth'

function AdminLoginPage() {
  const navigate = useNavigate()
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const response = await api.loginAdmin({ userId, password })
      setAdminAuth(response)
      setToast({ message: 'Login successful', type: 'success' })
      setTimeout(() => navigate('/admin'), 400)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-100 via-white to-cyan-100 p-4">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h1 className="mb-1 text-2xl font-bold text-slate-900">Admin Portal</h1>
        <p className="mb-5 text-sm text-slate-600">
          Manage tests, students, and results from one place.
        </p>

        <form onSubmit={onSubmit}>
          <input
            className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
          />
          <input
            type="password"
            className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error ? <p className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}
          <button className="w-full rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white transition hover:bg-indigo-700">
            Login
          </button>
        </form>

        <div className="my-4 flex items-center gap-3">
          <hr className="flex-1 border-slate-200" />
          <span className="text-xs text-slate-400">or</span>
          <hr className="flex-1 border-slate-200" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Link
            to="/admin/register"
            className="flex items-center justify-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z" />
            </svg>
            Add Admin User
          </Link>
          <Link
            to="/admin/forgot-password"
            className="flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
            Forgot Password
          </Link>
        </div>
      </div>
    </div>
  )
}

export default AdminLoginPage
