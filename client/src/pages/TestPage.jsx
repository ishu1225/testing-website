import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import QuestionCard from '../components/QuestionCard'
import Timer from '../components/Timer'
import Toast from '../components/Toast'
import WarningPopup from '../components/WarningPopup'
import { api } from '../services/api'
import { clearSession, loadSession, saveSession } from '../utils/storage'

function TestPage() {
  const { testId } = useParams()
  const navigate = useNavigate()
  const [testData, setTestData] = useState(null)
  const [answers, setAnswers] = useState({})
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState({ message: '', type: 'success' })
  const [tabSwitchCount, setTabSwitchCount] = useState(0)
  const [visitedQuestions, setVisitedQuestions] = useState({})
  const [currentQuestionId, setCurrentQuestionId] = useState(null)
  const submittedRef = useRef(false)
  const leftWindowRef = useRef(false)

  useEffect(() => {
    async function loadTest() {
      try {
        const session = loadSession(testId)
        if (!session?.studentName || !session?.regNumber || !session?.section) {
          navigate(`/test/${testId}`)
          return
        }
        if (session.submitted) {
          setError('You have already submitted this test.')
          return
        }

        const data = await api.getTest(testId)
        setTestData(data)
        setAnswers(session.answers || {})

        const total = data.duration * 60
        const elapsed = Math.floor((Date.now() - (session.startedAt || Date.now())) / 1000)
        setRemainingSeconds(Math.max(total - elapsed, 0))
        setTabSwitchCount(session.tabSwitchCount || 0)
        if (data.questions.length > 0) {
          setCurrentQuestionId(data.questions[0].id)
          setVisitedQuestions({ [data.questions[0].id]: true })
        }
      } catch (err) {
        setError(err.message)
      }
    }
    loadTest()
  }, [testId, navigate])

  useEffect(() => {
    if (!testData || submittedRef.current) return
    if (remainingSeconds <= 0) {
      handleSubmit(true)
      return
    }
    const timerId = setInterval(() => {
      setRemainingSeconds((prev) => prev - 1)
    }, 1000)
    return () => clearInterval(timerId)
  }, [remainingSeconds, testData])

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.hidden && !leftWindowRef.current) {
        leftWindowRef.current = true
        setTabSwitchCount((prev) => prev + 1)
      } else if (!document.hidden) {
        leftWindowRef.current = false
      }
    }

    const onBlur = () => {
      if (!leftWindowRef.current) {
        leftWindowRef.current = true
        setTabSwitchCount((prev) => prev + 1)
      }
    }

    const onFocus = () => {
      leftWindowRef.current = false
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('blur', onBlur)
    window.addEventListener('focus', onFocus)
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
      window.removeEventListener('blur', onBlur)
      window.removeEventListener('focus', onFocus)
    }
  }, [])

  useEffect(() => {
    const session = loadSession(testId)
    if (!session) return
    saveSession(testId, { ...session, answers, tabSwitchCount })
  }, [answers, tabSwitchCount, testId])

  const handleAnswerChange = (questionId, selected) => {
    setAnswers((prev) => ({ ...prev, [questionId]: selected }))
  }

  const jumpToQuestion = (questionId) => {
    const element = document.getElementById(`question-${questionId}`)
    if (element) {
      setCurrentQuestionId(questionId)
      setVisitedQuestions((prev) => ({ ...prev, [questionId]: true }))
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleSubmit = async (isAuto = false) => {
    if (submittedRef.current || submitting || !testData) return
    submittedRef.current = true
    setSubmitting(true)
    setError('')

    try {
      const session = loadSession(testId)
      const total = testData.duration * 60
      const timeTaken = Math.max(total - remainingSeconds, 0)
      await api.submitTest(testId, {
        studentName: session.studentName,
        regNumber: session.regNumber,
        section: session.section,
        answers,
        tabSwitchCount,
        timeTaken,
      })

      saveSession(testId, { ...session, answers, tabSwitchCount, submitted: true })
      clearSession(testId)
      setToast({
        message: isAuto ? 'Time is up. Test auto-submitted.' : 'Test submitted successfully.',
        type: 'success',
      })
      setTimeout(() => navigate(`/test/${testId}`), 900)
    } catch (err) {
      submittedRef.current = false
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (error) {
    return <div className="mx-auto mt-8 max-w-2xl rounded-lg bg-red-100 p-4 text-red-700">{error}</div>
  }

  if (!testData) return <div className="p-6">Loading test...</div>

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6">
      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: '', type: 'success' })} />
      <div className="sticky top-0 z-10 mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-100/90 p-2 backdrop-blur">
        <h1 className="text-2xl font-bold">{testData.name}</h1>
        <Timer remainingSeconds={remainingSeconds} />
      </div>

      <WarningPopup />

      <div className="mb-4 rounded-lg bg-white p-3 shadow-sm md:hidden">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Question Heatmap</p>
        <div className="flex flex-wrap gap-2">
          {testData.questions.map((q, idx) => {
            const isCurrent = currentQuestionId === q.id
            const answered = Boolean(answers[q.id])
            const visited = Boolean(visitedQuestions[q.id])
            const skipped = visited && !answered
            let classes = 'bg-white text-slate-700 border border-slate-200'
            if (answered) classes = 'bg-emerald-500 text-white border border-emerald-500'
            if (skipped) classes = 'bg-amber-400 text-slate-900 border border-amber-500'
            if (isCurrent) classes = 'bg-indigo-600 text-white border border-indigo-600 ring-2 ring-indigo-200'
            return (
              <button
                key={q.id}
                onClick={() => jumpToQuestion(q.id)}
                className={`h-9 min-w-9 rounded-md px-2 text-sm font-medium ${classes}`}
              >
                {idx + 1}
              </button>
            )
          })}
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs">
          <span className="rounded bg-indigo-100 px-2 py-1 text-indigo-800">Current</span>
          <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">Attempted</span>
          <span className="rounded bg-amber-100 px-2 py-1 text-amber-800">Visited/Skipped</span>
          <span className="rounded bg-slate-100 px-2 py-1 text-slate-700">Not Visited</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_240px] md:items-start">
        <div className="grid gap-4">
          {testData.questions.map((q, idx) => (
            <div key={q.id} id={`question-${q.id}`} className="scroll-mt-24">
              <QuestionCard
                question={q}
                index={idx}
                selectedOption={answers[q.id]}
                onAnswerChange={(questionId, selected) => {
                  setCurrentQuestionId(questionId)
                  setVisitedQuestions((prev) => ({ ...prev, [questionId]: true }))
                  handleAnswerChange(questionId, selected)
                }}
              />
            </div>
          ))}
        </div>

        <aside className="hidden rounded-xl bg-white p-3 shadow-sm md:sticky md:top-24 md:block">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Question Heatmap</p>
          <div className="flex flex-wrap gap-2">
            {testData.questions.map((q, idx) => {
              const isCurrent = currentQuestionId === q.id
              const answered = Boolean(answers[q.id])
              const visited = Boolean(visitedQuestions[q.id])
              const skipped = visited && !answered
              let classes = 'bg-white text-slate-700 border border-slate-200'
              if (answered) classes = 'bg-emerald-500 text-white border border-emerald-500'
              if (skipped) classes = 'bg-amber-400 text-slate-900 border border-amber-500'
              if (isCurrent) classes = 'bg-indigo-600 text-white border border-indigo-600 ring-2 ring-indigo-200'
              return (
                <button
                  key={q.id}
                  onClick={() => jumpToQuestion(q.id)}
                  className={`h-9 min-w-9 rounded-md px-2 text-sm font-medium ${classes}`}
                >
                  {idx + 1}
                </button>
              )
            })}
          </div>
        </aside>
      </div>

      <button
        onClick={() => handleSubmit(false)}
        disabled={submitting}
        className="mt-6 hidden rounded-lg bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300 sm:inline-block"
      >
        {submitting ? 'Submitting...' : 'Submit Test'}
      </button>

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white p-3 shadow-[0_-4px_12px_rgba(15,23,42,0.08)] sm:hidden">
        <button
          onClick={() => handleSubmit(false)}
          disabled={submitting}
          className="w-full rounded-lg bg-emerald-600 px-4 py-3 text-base font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
        >
          {submitting ? 'Submitting...' : 'Submit Test'}
        </button>
      </div>
      <div className="h-20 sm:hidden" />
    </div>
  )
}

export default TestPage
