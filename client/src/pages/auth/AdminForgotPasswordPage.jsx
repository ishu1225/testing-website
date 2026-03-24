import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'

function AdminForgotPasswordPage() {
  const [form, setForm] = useState({ userId: '', email: '', newPassword: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.forgotPassword(form)
      setMessage('Password reset successful. Login with your new password.')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-amber-50 to-indigo-100 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h1 className="mb-1 text-2xl font-bold">Forgot Password</h1>
        <p className="mb-4 text-sm text-slate-600">Reset using linked email</p>
        <input className="mb-3 w-full rounded border px-3 py-2" placeholder="User ID" value={form.userId} onChange={(e) => setForm({ ...form, userId: e.target.value })} required />
        <input type="email" className="mb-3 w-full rounded border px-3 py-2" placeholder="Linked Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <input type="password" className="mb-4 w-full rounded border px-3 py-2" placeholder="New Password" value={form.newPassword} onChange={(e) => setForm({ ...form, newPassword: e.target.value })} required />
        {error ? <p className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="mb-3 rounded bg-emerald-100 p-2 text-sm text-emerald-700">{message}</p> : null}
        <button className="w-full rounded-lg bg-indigo-600 py-2 text-white">Reset Password</button>
        <Link to="/admin/login" className="mt-3 block text-center text-sm text-indigo-700">Back to Login</Link>
      </form>
    </div>
  )
}

export default AdminForgotPasswordPage
