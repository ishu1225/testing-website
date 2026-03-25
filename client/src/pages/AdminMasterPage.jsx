import { useEffect, useState } from 'react'
import Toast from '../components/Toast'
import { api } from '../services/api'
import { getAdminAuth } from '../utils/adminAuth'

function AdminMasterPage() {
  const adminUserId = getAdminAuth()?.admin?.userId || ''
  const isMaster = adminUserId.toUpperCase() === 'ISHU'

  const [admins, setAdmins] = useState([])
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const [loading, setLoading] = useState(true)
  const [resetPasswords, setResetPasswords] = useState({})

  useEffect(() => {
    setLoading(true)
    setError('')
    api
      .getAllAdmins()
      .then(setAdmins)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const onResetPassword = async (adminId) => {
    const newPassword = (resetPasswords[adminId] || '').trim()
    if (!newPassword) {
      setError('Enter a new password for that admin')
      return
    }
    setError('')
    try {
      await api.masterResetAdminPassword(adminId, { newPassword })
      setToast({ message: 'Password updated', type: 'success' })
      setResetPasswords((prev) => ({ ...prev, [adminId]: '' }))
    } catch (err) {
      setError(err.message)
      setToast({ message: '', type: 'success' })
    }
  }

  const onDeleteAccount = async (admin) => {
    const ok = window.confirm(`Delete admin ${admin.userId} and all their tests/results? This cannot be undone.`)
    if (!ok) return
    setError('')
    try {
      await api.masterDeleteAdminAccount(admin.id)
      setToast({ message: 'Admin deleted', type: 'success' })
      // Refresh table
      setAdmins((prev) => prev.filter((x) => x.id !== admin.id))
    } catch (err) {
      setError(err.message)
      setToast({ message: '', type: 'success' })
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />

      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Master Admin</h1>
        <div className="text-sm text-slate-600">
          Logged in as <span className="font-semibold">{adminUserId}</span>
        </div>
      </div>

      {error ? <p className="mb-4 rounded bg-red-100 p-3 text-red-700">{error}</p> : null}

      {loading ? (
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold text-slate-700">Loading admins...</p>
          <div className="mt-4 h-2 w-full animate-pulse rounded bg-slate-100" />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-4 py-3">User ID</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Reset Password</th>
              </tr>
            </thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a.id} className="border-t border-slate-200 transition hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-800">{a.userId}</td>
                  <td className="px-4 py-3 text-slate-600">{a.email}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="password"
                        className="w-56 rounded-lg border border-slate-300 px-3 py-2"
                        placeholder={`New password for ${a.userId}`}
                        value={resetPasswords[a.id] || ''}
                        onChange={(e) => setResetPasswords((prev) => ({ ...prev, [a.id]: e.target.value }))}
                        disabled={!isMaster}
                      />
                      <button
                        onClick={() => onResetPassword(a.id)}
                        disabled={!isMaster}
                        className="rounded-lg bg-indigo-600 px-3 py-2 text-white transition hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed"
                      >
                        Update
                      </button>
                      <button
                        onClick={() => onDeleteAccount(a)}
                        disabled={!isMaster || a.userId.toUpperCase() === 'ISHU'}
                        className="rounded-lg bg-rose-600 px-3 py-2 text-white transition hover:bg-rose-700 disabled:bg-rose-300 disabled:cursor-not-allowed"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {admins.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-center text-slate-500" colSpan={3}>
                    No admins found.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default AdminMasterPage

