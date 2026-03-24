import { useState } from 'react'
import { Link } from 'react-router-dom'
import Toast from '../components/Toast'
import { api } from '../services/api'

function CreateTestPage() {
  const [name, setName] = useState('')
  const [duration, setDuration] = useState(30)
  const [expiryValue, setExpiryValue] = useState(1)
  const [expiryUnit, setExpiryUnit] = useState('days')
  const [rawQuestions, setRawQuestions] = useState('')
  const [created, setCreated] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState({ message: '', type: 'success' })

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setCreated(null)
    setLoading(true)
    try {
      const result = await api.createTest({
        name,
        duration: Number(duration),
        expiryValue: Number(expiryValue),
        expiryUnit,
        rawQuestions,
      })
      setCreated(result)
      setName('')
      setDuration(30)
      setExpiryValue(1)
      setExpiryUnit('days')
      setRawQuestions('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const copyTestLink = async () => {
    if (!created) return
    const link = `${window.location.origin}/test/${created.id}`
    try {
      await navigator.clipboard.writeText(link)
      setToast({ message: 'Test link copied', type: 'success' })
    } catch {
      setToast({ message: 'Could not copy link', type: 'error' })
    }
  }

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Create Test</h1>
        <Link to="/admin" className="rounded-lg bg-slate-200 px-4 py-2 text-slate-900">
          Back
        </Link>
      </div>

      <form onSubmit={onSubmit} className="rounded-xl bg-white p-5 shadow-sm">
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium">Test Name</label>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium">Duration (minutes)</label>
          <input
            type="number"
            min={1}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            required
          />
        </div>
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium">Link Expires In</label>
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              className="w-1/2 rounded-lg border border-slate-300 px-3 py-2"
              value={expiryValue}
              onChange={(e) => setExpiryValue(e.target.value)}
              required
            />
            <select
              className="w-1/2 rounded-lg border border-slate-300 px-3 py-2"
              value={expiryUnit}
              onChange={(e) => setExpiryUnit(e.target.value)}
            >
              <option value="hours">Hours</option>
              <option value="days">Days</option>
            </select>
          </div>
        </div>
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium">Questions (raw text)</label>
          <textarea
            rows={14}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            value={rawQuestions}
            onChange={(e) => setRawQuestions(e.target.value)}
            placeholder="Q1. ...&#10;A. ...&#10;B. ...&#10;C. ...&#10;D. ...&#10;Answer: B"
            required
          />
        </div>

        <button
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2 text-white disabled:bg-slate-500"
        >
          {loading ? 'Creating...' : 'Create Test'}
        </button>
      </form>

      {error ? <p className="mt-4 rounded bg-red-100 p-3 text-red-700">{error}</p> : null}
      {created ? (
        <div className="mt-4 rounded bg-emerald-100 p-3 text-emerald-800">
          <p className="mb-2">
            Test created. Student link: <strong>{`${window.location.origin}/test/${created.id}`}</strong>
          </p>
          <p className="mb-2 text-sm">Link expires at: {new Date(created.expiresAt).toLocaleString()}</p>
          <button
            onClick={copyTestLink}
            className="rounded bg-emerald-700 px-3 py-1 text-white hover:bg-emerald-800"
          >
            Copy Link
          </button>
        </div>
      ) : null}
    </div>
  )
}

export default CreateTestPage
