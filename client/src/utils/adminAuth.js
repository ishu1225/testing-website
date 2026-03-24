const ADMIN_AUTH_KEY = 'admin_auth'

export function getAdminAuth() {
  const raw = localStorage.getItem(ADMIN_AUTH_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setAdminAuth(value) {
  localStorage.setItem(ADMIN_AUTH_KEY, JSON.stringify(value))
}

export function clearAdminAuth() {
  localStorage.removeItem(ADMIN_AUTH_KEY)
}

export function getAdminToken() {
  return getAdminAuth()?.token || ''
}
