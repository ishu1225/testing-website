import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'

function AdminChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (newPassword !== confirmPassword) {
      setError('New password and confirm password do not match')
      return
    }
    try {
      await api.changePassword({ currentPassword, newPassword })
      setMessage('Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="mx-auto max-w-xl p-4 sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Change Password</h1>
        <Link to="/admin" className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-800">
          Back
        </Link>
      </div>
      <form onSubmit={onSubmit} className="rounded-xl bg-white p-5 shadow-sm">
        <input
          type="password"
          placeholder="Current Password"
          className="mb-3 w-full rounded border px-3 py-2"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="New Password"
          className="mb-3 w-full rounded border px-3 py-2"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Confirm New Password"
          className="mb-4 w-full rounded border px-3 py-2"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />
        {error ? <p className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}
        {message ? <p className="mb-3 rounded bg-emerald-100 p-2 text-sm text-emerald-700">{message}</p> : null}
        <button className="rounded-lg bg-indigo-600 px-4 py-2 text-white">Update Password</button>
      </form>
    </div>
  )
}

export default AdminChangePasswordPage
