const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
import { getAdminToken } from '../utils/adminAuth'

async function request(path, options = {}) {
  const token = getAdminToken()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message = payload?.error || payload?.message || 'Request failed'
    throw new Error(message)
  }
  return payload
}

async function requestBlob(path, options = {}) {
  const token = getAdminToken()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    let message = 'Request failed'
    try {
      const data = await response.json()
      message = data?.error || data?.message || message
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(message)
  }
  return response.blob()
}

export const api = {
  registerAdmin: (data) =>
    request('/api/admin/register', { method: 'POST', body: JSON.stringify(data) }),
  verifyAdminEmail: (data) =>
    request('/api/admin/verify-email', { method: 'POST', body: JSON.stringify(data) }),
  loginAdmin: (data) =>
    request('/api/admin/login', { method: 'POST', body: JSON.stringify(data) }),
  forgotPassword: (data) =>
    request('/api/admin/forgot-password', { method: 'POST', body: JSON.stringify(data) }),
  resetPassword: (data) =>
    request('/api/admin/forgot-password/reset-password', { method: 'POST', body: JSON.stringify(data) }),
  requestPasswordResetOtp: (data) =>
    request('/api/admin/forgot-password/request-otp', { method: 'POST', body: JSON.stringify(data) }),
  confirmPasswordResetOtp: (data) =>
    request('/api/admin/forgot-password/confirm-otp', { method: 'POST', body: JSON.stringify(data) }),
  changePassword: (data) =>
    request('/api/admin/change-password', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/api/admin/me'),
  createTest: (data) =>
    request('/api/tests', { method: 'POST', body: JSON.stringify(data) }),
  getTests: () => request('/api/tests'),
  getTest: (testId) => request(`/api/tests/${testId}`),
  submitTest: (testId, data) =>
    request(`/api/tests/${testId}/submit`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getResults: (testId) => request(`/api/tests/${testId}/results`),
  getWrongAnswers: (testId) => request(`/api/tests/${testId}/wrong-answers`),
  deleteTest: (testId) => request(`/api/tests/${testId}`, { method: 'DELETE' }),
  deleteAdminAccount: () => request(`/api/admin/account`, { method: 'DELETE' }),
  getCsvExportUrl: (testId) =>
    `${API_BASE_URL}/api/tests/${testId}/results/export/csv?token=${encodeURIComponent(getAdminToken())}`,
  getXlsxExportUrl: (testId) =>
    `${API_BASE_URL}/api/tests/${testId}/results/export/xlsx?token=${encodeURIComponent(getAdminToken())}`,
  getResultsPdfUrl: (testId) =>
    `${API_BASE_URL}/api/tests/${testId}/results/export/pdf?token=${encodeURIComponent(getAdminToken())}`,
  downloadResultsPdf: (testId) => requestBlob(`/api/tests/${testId}/results/export/pdf`),
  getSubmissionPdfUrl: (submissionId) =>
    `${API_BASE_URL}/api/submissions/${submissionId}/pdf?token=${encodeURIComponent(getAdminToken())}`,
  getAllAdmins: () => request('/api/master-admin/admins'),
  masterResetAdminPassword: (adminId, data) =>
    request(`/api/master-admin/admins/${adminId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  masterDeleteAdminAccount: (adminId) =>
    request(`/api/master-admin/admins/${adminId}/account`, {
      method: 'DELETE',
    }),
}
