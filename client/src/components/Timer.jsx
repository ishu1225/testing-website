function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60)
  const secs = totalSeconds % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function Timer({ remainingSeconds }) {
  return (
    <div className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
      Time Left: {formatTime(Math.max(remainingSeconds, 0))}
    </div>
  )
}

export default Timer
