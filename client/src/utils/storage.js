const SESSION_KEY_PREFIX = 'test_session_'

export function saveSession(testId, sessionData) {
  localStorage.setItem(`${SESSION_KEY_PREFIX}${testId}`, JSON.stringify(sessionData))
}

export function loadSession(testId) {
  const raw = localStorage.getItem(`${SESSION_KEY_PREFIX}${testId}`)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function clearSession(testId) {
  localStorage.removeItem(`${SESSION_KEY_PREFIX}${testId}`)
}
