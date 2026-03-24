import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Toast from '../components/Toast'
import { api } from '../services/api'

function AdminDashboardPage() {
  const [tests, setTests] = useState([])
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })

  useEffect(() => {
    loadTests()
  }, [])

  const loadTests = () => {
    api
      .getTests()
      .then(setTests)
      .catch((err) => setError(err.message))
  }

  const copyTestLink = async (testId) => {
    const link = `${window.location.origin}/test/${testId}`
    try {
      await navigator.clipboard.writeText(link)
      setToast({ message: 'Student link copied', type: 'success' })
    } catch {
      setToast({ message: 'Could not copy link', type: 'error' })
    }
  }

  const deleteTest = async (testId) => {
    const confirmed = window.confirm('Delete this test and all related submissions?')
    if (!confirmed) return
    try {
      await api.deleteTest(testId)
      setToast({ message: 'Test deleted successfully', type: 'success' })
      loadTests()
    } catch (err) {
      setToast({ message: err.message, type: 'error' })
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Admin Dashboard</h1>
        <Link to="/admin/create-test" className="rounded-lg bg-slate-900 px-4 py-2 text-white">
          Create Test
        </Link>
      </div>

      {error ? <p className="mb-4 rounded bg-red-100 p-3 text-red-700">{error}</p> : null}

      <div className="hidden overflow-x-auto rounded-xl bg-white shadow-sm md:block">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-4 py-3">Test Name</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Questions</th>
              <th className="px-4 py-3">Expiry</th>
              <th className="px-4 py-3">Student Link</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tests.map((test) => (
              <tr key={test.id} className="border-t border-slate-200">
                <td className="px-4 py-3 font-medium text-slate-800">{test.name}</td>
                <td className="px-4 py-3">{test.duration} mins</td>
                <td className="px-4 py-3">{test.questionCount}</td>
                <td className="px-4 py-3">
                  <span className={test.isExpired ? 'text-rose-700' : 'text-emerald-700'}>
                    {test.expiresAt ? new Date(test.expiresAt).toLocaleString() : '-'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="max-w-[280px] truncate">{`${window.location.origin}/test/${test.id}`}</span>
                    <button
                      onClick={() => copyTestLink(test.id)}
                      className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-300"
                    >
                      Copy
                    </button>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`/admin/tests/${test.id}/results`}
                    className="rounded bg-blue-600 px-3 py-1 text-white"
                  >
                    View Results
                  </Link>
                  <button
                    onClick={() => deleteTest(test.id)}
                    className="ml-2 rounded bg-rose-600 px-3 py-1 text-white"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {tests.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-6 text-center text-slate-500">
                  No tests created yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 md:hidden">
        {tests.map((test) => {
          const link = `${window.location.origin}/test/${test.id}`
          return (
            <div key={test.id} className="rounded-xl bg-white p-4 shadow-sm">
              <p className="text-base font-semibold text-slate-800">{test.name}</p>
              <p className="mt-1 text-sm text-slate-600">Duration: {test.duration} mins</p>
              <p className="text-sm text-slate-600">Questions: {test.questionCount}</p>
              <p className={`text-sm ${test.isExpired ? 'text-rose-700' : 'text-emerald-700'}`}>
                Expires: {test.expiresAt ? new Date(test.expiresAt).toLocaleString() : '-'}
              </p>

              <div className="mt-3 rounded-lg bg-slate-50 p-2 text-xs text-slate-700">
                <p className="mb-1 font-medium">Student Link</p>
                <p className="break-all">{link}</p>
              </div>

              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => copyTestLink(test.id)}
                  className="rounded bg-slate-200 px-3 py-1.5 text-sm text-slate-800"
                >
                  Copy Link
                </button>
                <Link
                  to={`/admin/tests/${test.id}/results`}
                  className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white"
                >
                  View Results
                </Link>
                <button
                  onClick={() => deleteTest(test.id)}
                  className="rounded bg-rose-600 px-3 py-1.5 text-sm text-white"
                >
                  Delete
                </button>
              </div>
            </div>
          )
        })}
        {tests.length === 0 ? (
          <div className="rounded-xl bg-white p-6 text-center text-slate-500 shadow-sm">
            No tests created yet.
          </div>
        ) : null}
      </div>
    </div>
  )
}

export default AdminDashboardPage
