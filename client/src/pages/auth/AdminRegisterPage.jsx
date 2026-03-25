import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'

function AdminRegisterPage() {
  const navigate = useNavigate()
  const [userId, setUserId] = useState('')
  const [password, setPassword] = useState('')
  const [dob, setDob] = useState('')
  const [birthCity, setBirthCity] = useState('')
  const [schoolName, setSchoolName] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      const res = await api.registerAdmin({ userId, password, dob, birthCity, schoolName })
      setMessage(res?.message || 'Admin account created.')
      setTimeout(() => navigate('/admin/login'), 600)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-indigo-100 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <h1 className="mb-4 text-2xl font-bold">Create Admin Account</h1>
        <form onSubmit={onSubmit}>
          <input
            className="mb-3 w-full rounded border px-3 py-2"
            placeholder="User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
            autoFocus
          />
          <input
            type="password"
            className="mb-3 w-full rounded border px-3 py-2"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
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
          {message ? <p className="mb-3 rounded bg-emerald-100 p-2 text-sm text-emerald-700">{message}</p> : null}
          <button type="submit" className="w-full rounded-lg bg-indigo-600 py-2 text-white transition hover:bg-indigo-700">
            Create Account
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <a href="/admin/login" className="font-medium text-indigo-700 hover:underline">Login</a>
        </p>
      </div>
    </div>
  )
}

export default AdminRegisterPage
