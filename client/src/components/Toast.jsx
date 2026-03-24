import { useEffect } from 'react'

function Toast({ message, type = 'success', onClose }) {
  useEffect(() => {
    if (!message) return
    const id = setTimeout(() => onClose(), 2200)
    return () => clearTimeout(id)
  }, [message, onClose])

  if (!message) return null

  const styles =
    type === 'error'
      ? 'border-red-300 bg-red-100 text-red-700'
      : 'border-emerald-300 bg-emerald-100 text-emerald-700'

  return (
    <div className={`fixed right-4 top-4 z-50 rounded-lg border px-4 py-2 text-sm shadow ${styles}`}>
      {message}
    </div>
  )
}

export default Toast
