import { useState } from 'react'
import { Link } from 'react-router-dom'
import Toast from '../../components/Toast'
import { api } from '../../services/api'

function AdminForgotPasswordPage() {
  const [userId, setUserId] = useState('')
  const [dob, setDob] = useState('')
  const [birthCity, setBirthCity] = useState('')
  const [schoolName, setSchoolName] = useState('')

  const [otpRequested, setOtpRequested] = useState(false)
  const [otp, setOtp] = useState('')
  const [devOtp, setDevOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const [loading, setLoading] = useState(false)

  const onRequestOtp = async (e) => {
    e.preventDefault()
    setError('')
    setDevOtp('')
    setLoading(true)
    try {
      const res = await api.requestPasswordResetOtp({ userId, dob, birthCity, schoolName })
      if (res?.otp) setDevOtp(res.otp)
      setOtpRequested(true)
      setToast({ message: res?.message || 'OTP requested', type: 'success' })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const onConfirmOtp = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (newPassword !== confirmPassword) {
        setError('New password and confirm password do not match')
        return
      }
      await api.confirmPasswordResetOtp({ userId, otp, newPassword })
      setToast({ message: 'Password reset successful', type: 'success' })
      // After reset, send user back to login.
      setTimeout(() => {
        window.location.href = '/admin/login'
      }, 500)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-amber-50 to-indigo-100 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
        <h1 className="mb-3 text-2xl font-bold">Reset Admin Password</h1>
        <p className="mb-4 text-sm text-slate-600">
          Answer your security questions, then reset password using an email OTP.
        </p>

        {!otpRequested ? (
          <form onSubmit={onRequestOtp}>
            <input
              className="mb-3 w-full rounded border px-3 py-2"
              placeholder="User ID"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              required
              autoFocus
            />
            <input
              type="date"
              className="mb-3 w-full rounded border px-3 py-2"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              required
            />
            <input
              className="mb-3 w-full rounded border px-3 py-2"
              placeholder="City of birth"
              value={birthCity}
              onChange={(e) => setBirthCity(e.target.value)}
              required
            />
            <input
              className="mb-3 w-full rounded border px-3 py-2"
              placeholder="Name of school"
              value={schoolName}
              onChange={(e) => setSchoolName(e.target.value)}
              required
            />
            {error ? <p className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}

            {devOtp ? (
              <div className="mb-3 rounded bg-emerald-50 p-3 text-sm text-emerald-800">
                Dev OTP: <span className="font-bold">{devOtp}</span>
              </div>
            ) : null}

            <button
              disabled={loading}
              className="w-full rounded-lg bg-indigo-600 py-2 text-white transition hover:bg-indigo-700 disabled:bg-indigo-400"
            >
              {loading ? 'Requesting...' : 'Request OTP'}
            </button>
            <div className="mt-3 text-center text-sm text-slate-600">
              <Link to="/admin/login" className="font-medium text-indigo-700 hover:text-indigo-800">
                Back to Login
              </Link>
            </div>
          </form>
        ) : (
          <form onSubmit={onConfirmOtp}>
            <input
              className="mb-3 w-full rounded border px-3 py-2"
              placeholder="Enter OTP code"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              required
              autoFocus
            />
            <input
              type="password"
              className="mb-3 w-full rounded border px-3 py-2"
              placeholder="New Password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <input
              type="password"
              className="mb-4 w-full rounded border px-3 py-2"
              placeholder="Confirm New Password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
            {error ? <p className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</p> : null}

            {devOtp ? (
              <div className="mb-3 rounded bg-emerald-50 p-3 text-sm text-emerald-800">
                Dev OTP: <span className="font-bold">{devOtp}</span>
              </div>
            ) : null}

            <button
              disabled={loading}
              className="w-full rounded-lg bg-emerald-600 py-2 text-white transition hover:bg-emerald-700 disabled:bg-emerald-400"
            >
              {loading ? 'Resetting...' : 'Reset Password'}
            </button>
            <div className="mt-3 text-center text-sm text-slate-600">
              <button
                type="button"
                className="font-medium text-indigo-700 hover:text-indigo-800"
                onClick={() => {
                  setOtpRequested(false)
                  setOtp('')
                  setNewPassword('')
                  setConfirmPassword('')
                }}
              >
                Back
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default AdminForgotPasswordPage
