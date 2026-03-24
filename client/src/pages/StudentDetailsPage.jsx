import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../services/api'
import { loadSession, saveSession } from '../utils/storage'

function StudentDetailsPage() {
  const { testId } = useParams()
  const navigate = useNavigate()
  const existing = loadSession(testId)
  const [studentName, setStudentName] = useState(existing?.studentName || '')
  const [regNumber, setRegNumber] = useState(existing?.regNumber || '')
  const [section, setSection] = useState(existing?.section || '')
  const [loadError, setLoadError] = useState('')
  const [testMeta, setTestMeta] = useState(null)

  useEffect(() => {
    api
      .getTest(testId)
      .then(setTestMeta)
      .catch((err) => setLoadError(err.message))
  }, [testId])

  const onSubmit = (e) => {
    e.preventDefault()
    if (!studentName || !regNumber || !section) return

    saveSession(testId, {
      ...existing,
      studentName,
      regNumber,
      section,
      startedAt: existing?.startedAt || Date.now(),
      tabSwitchCount: existing?.tabSwitchCount || 0,
      submitted: existing?.submitted || false,
      answers: existing?.answers || {},
    })

    navigate(`/test/${testId}/attempt`)
  }

  return (
    <div className="mx-auto max-w-xl p-4 sm:p-6">
      <h1 className="mb-2 text-2xl font-bold">Student Details</h1>
      <p className="mb-6 text-sm text-slate-600">Test ID: {testId}</p>
      {loadError ? <p className="mb-4 rounded bg-red-100 p-3 text-red-700">{loadError}</p> : null}
      {testMeta?.expiresAt ? (
        <p className="mb-4 rounded bg-amber-50 p-3 text-sm text-amber-800">
          Test link expires at: {new Date(testMeta.expiresAt).toLocaleString()}
        </p>
      ) : null}
      <form onSubmit={onSubmit} className="rounded-xl bg-white p-5 shadow-sm">
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium">Name</label>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            value={studentName}
            onChange={(e) => setStudentName(e.target.value)}
            required
          />
        </div>
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium">Registration Number</label>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            value={regNumber}
            onChange={(e) => setRegNumber(e.target.value)}
            required
          />
        </div>
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium">Section</label>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            value={section}
            onChange={(e) => setSection(e.target.value)}
            required
          />
        </div>
        <button
          disabled={Boolean(loadError)}
          className="rounded-lg bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          Start Test
        </button>
      </form>
    </div>
  )
}

export default StudentDetailsPage
