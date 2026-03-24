import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Toast from '../components/Toast'
import { api } from '../services/api'

function formatSeconds(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60)
  const secs = totalSeconds % 60
  return `${mins}m ${secs}s`
}

function formatSubmittedAt(isoDate) {
  if (!isoDate) return '-'
  const normalized = /Z$|[+-]\d\d:\d\d$/.test(isoDate) ? isoDate : `${isoDate}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return isoDate
  return date.toLocaleString()
}

function ResultsPage() {
  const { testId } = useParams()
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })

  useEffect(() => {
    api
      .getResults(testId)
      .then(setResults)
      .catch((err) => setError(err.message))
  }, [testId])

  const onDownloadPdf = async () => {
    try {
      const blob = await api.downloadResultsPdf(testId)
      const url = window.URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `test_${testId}_results_report.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(url)
      setToast({ message: 'PDF downloaded', type: 'success' })
    } catch (err) {
      setToast({ message: err.message, type: 'error' })
    }
  }

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Results - Test {testId}</h1>
        <div className="flex items-center gap-2">
          <Link to="/admin" className="rounded-lg bg-slate-200 px-4 py-2 text-slate-900">
            Back
          </Link>
          <a
            href={api.getCsvExportUrl(testId)}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-white"
          >
            Export Excel (CSV)
          </a>
          <button
            onClick={onDownloadPdf}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-white"
          >
            Download Full PDF Report
          </button>
        </div>
      </div>

      {error ? <p className="mb-4 rounded bg-red-100 p-3 text-red-700">{error}</p> : null}

      <div className="hidden overflow-x-auto rounded-xl bg-white shadow-sm md:block">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Registration Number</th>
              <th className="px-4 py-3">Section</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Tab Switch Count</th>
              <th className="px-4 py-3">Time Taken</th>
              <th className="px-4 py-3">Submitted At</th>
            </tr>
          </thead>
          <tbody>
            {results.map((row) => (
              <tr key={row.id} className="border-t border-slate-200">
                <td className="px-4 py-3">{row.studentName}</td>
                <td className="px-4 py-3">{row.regNumber}</td>
                <td className="px-4 py-3">{row.section}</td>
                <td className="px-4 py-3">{row.score}</td>
                <td className="px-4 py-3">{row.tabSwitchCount}</td>
                <td className="px-4 py-3">{formatSeconds(row.timeTaken)}</td>
                <td className="px-4 py-3">{formatSubmittedAt(row.submittedAt)}</td>
              </tr>
            ))}
            {results.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-6 text-center text-slate-500">
                  No submissions yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 md:hidden">
        {results.map((row) => (
          <div key={row.id} className="rounded-xl bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-slate-800">{row.studentName}</p>
                <p className="text-xs text-slate-500">{row.regNumber}</p>
              </div>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">
                Section {row.section}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <p className="text-slate-600">Score</p>
              <p className="font-medium text-slate-800">{row.score}</p>
              <p className="text-slate-600">Tab Switches</p>
              <p className="font-medium text-slate-800">{row.tabSwitchCount}</p>
              <p className="text-slate-600">Time Taken</p>
              <p className="font-medium text-slate-800">{formatSeconds(row.timeTaken)}</p>
              <p className="text-slate-600">Submitted</p>
              <p className="font-medium text-slate-800">{formatSubmittedAt(row.submittedAt)}</p>
            </div>

          </div>
        ))}
        {results.length === 0 ? (
          <div className="rounded-xl bg-white p-6 text-center text-slate-500 shadow-sm">
            No submissions yet.
          </div>
        ) : null}
      </div>
    </div>
  )
}

export default ResultsPage
