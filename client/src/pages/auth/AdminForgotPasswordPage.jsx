import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Toast from '../../components/Toast'
import { api } from '../../services/api'

function AdminForgotPasswordPage() {
  const navigate = useNavigate()
  const [userId, setUserId] = useState('')
  const [dob, setDob] = useState('')
  const [birthCity, setBirthCity] = useState('')
  const [schoolName, setSchoolName] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const [loading, setLoading] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      await api.resetPassword({ userId, dob, birthCity, schoolName, newPassword })
      setToast({ message: 'Password reset successfully! Redirecting...', type: 'success' })
      setTimeout(() => navigate('/admin/login'), 1200)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-amber-50 to-indigo-100 p-4">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h1 className="mb-1 text-2xl font-bold text-slate-900">Reset Password</h1>
        <p className="mb-5 text-sm text-slate-600">
          Verify your identity using the details you registered with, then set a new password.
        </p>

        <form onSubmit={onSubmit}>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">User ID</label>
          <input
            className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Your User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
            autoFocus
          />

          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Date of Birth</label>
          <input
            type="date"
            className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            value={dob}
            onChange={(e) => setDob(e.target.value)}
            required
          />

          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">City of Birth</label>
          <input
            className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="e.g. Delhi"
            value={birthCity}
            onChange={(e) => setBirthCity(e.target.value)}
            required
          />

          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">School Name</label>
          <input
            className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Name of school you registered with"
            value={schoolName}
            onChange={(e) => setSchoolName(e.target.value)}
            required
          />

          <div className="my-3 flex items-center gap-3">
            <hr className="flex-1 border-slate-200" />
            <span className="text-xs text-slate-400">new password</span>
            <hr className="flex-1 border-slate-200" />
          </div>

          <input
            type="password"
            className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="New Password (min 6 characters)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          <input
            type="password"
            className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Confirm New Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />

          {error ? <p className="mb-3 rounded-lg bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-indigo-600 py-2 font-medium text-white transition hover:bg-indigo-700 disabled:bg-indigo-400"
          >
            {loading ? 'Verifying...' : 'Reset Password'}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-slate-600">
          <Link to="/admin/login" className="font-medium text-indigo-700 hover:text-indigo-800">
            ← Back to Login
          </Link>
        </div>
      </div>
    </div>
  )
}

export default AdminForgotPasswordPage
