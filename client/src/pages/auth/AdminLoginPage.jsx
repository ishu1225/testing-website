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
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h1 className="mb-1 text-2xl font-bold text-slate-900">Admin Login</h1>
        <p className="mb-5 text-sm text-slate-600">Use your admin user ID and password</p>
        <input
          className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          required
        />
        <input
          type="password"
          className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error ? <p className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}
        <button className="w-full rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white">Login</button>
        <div className="mt-4 flex justify-between text-sm">
          <Link to="/admin/register" className="text-indigo-700">Create Admin</Link>
          <Link to="/admin/forgot-password" className="text-indigo-700">Forgot Password</Link>
        </div>
      </form>
    </div>
  )
}

export default AdminLoginPage
