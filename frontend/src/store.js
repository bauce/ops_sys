import { reactive } from 'vue'
import { api } from './api'

export const auth = reactive({
  staff: null,
  ready: false,
  loading: false,
})

export async function ensureAuth(force = false) {
  if (auth.ready && !force) return auth.staff
  auth.loading = true
  try {
    auth.staff = await api.me()
  } catch (e) {
    auth.staff = null
  } finally {
    auth.loading = false
    auth.ready = true
  }
  return auth.staff
}

export function setStaff(staff) {
  auth.staff = staff
  auth.ready = true
}

export function clearAuth() {
  auth.staff = null
  auth.ready = true
}
