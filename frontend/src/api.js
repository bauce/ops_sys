const jsonHeaders = { 'Content-Type': 'application/json' }

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function req(path, opts = {}) {
  const { method = 'GET', body, params } = opts
  let url = path
  if (params) {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.append(k, v)
    })
    const s = q.toString()
    if (s) url += (url.includes('?') ? '&' : '?') + s
  }
  const res = await fetch(url, {
    method,
    credentials: 'include',
    headers: body !== undefined ? jsonHeaders : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let msg = `请求失败（${res.status}）`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') msg = data.detail
      else if (Array.isArray(data.detail)) msg = '提交内容不完整，请检查必填项'
      else if (data.detail) msg = '操作失败'
    } catch (e) {
      /* ignore */
    }
    throw new ApiError(msg, res.status)
  }
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res.text()
}

export const api = {
  // ---------- 报障人（免登录，Cookie 身份） ----------
  room: (qr) => req(`/api/public/room/${encodeURIComponent(qr)}`),
  meta: () => req('/api/public/meta'),
  createTicket: (data) => req('/api/public/tickets', { method: 'POST', body: data }),
  myTickets: () => req('/api/public/my-tickets'),
  publicTicket: (code, tail) => req(`/api/public/ticket/${encodeURIComponent(code)}`, { params: { tail } }),
  lookup: (tail, roomId) => req('/api/public/lookup', { params: { tail, room_id: roomId } }),
  confirmTicket: (code, data, tail) =>
    req(`/api/public/ticket/${encodeURIComponent(code)}/confirm`, { method: 'POST', body: data, params: { tail } }),
  cancelTicket: (code) => req(`/api/public/ticket/${encodeURIComponent(code)}/cancel`, { method: 'POST' }),

  // ---------- 运维人员 ----------
  login: (username, password) => req('/api/staff/login', { method: 'POST', body: { username, password } }),
  loginOptions: () => req('/api/staff/login-options'),
  logout: () => req('/api/staff/logout', { method: 'POST' }),
  me: () => req('/api/staff/me'),
  users: () => req('/api/staff/users'),
  createUser: (data) => req('/api/staff/users', { method: 'POST', body: data }),
  updateUser: (id, data) => req(`/api/staff/users/${id}`, { method: 'PUT', body: data }),
  settings: () => req('/api/staff/settings'),
  saveSettings: (data) => req('/api/staff/settings', { method: 'PUT', body: data }),
  emailSettings: () => req('/api/staff/settings/email'),
  saveEmailSettings: (data) => req('/api/staff/settings/email', { method: 'PUT', body: data }),
  testEmail: (to) => req('/api/staff/settings/email/test', { method: 'POST', body: { to } }),

  // ---------- 工单 ----------
  tickets: (params) => req('/api/staff/tickets', { params }),
  ticket: (id) => req(`/api/staff/tickets/${id}`),
  acceptTicket: (id, assignee_id) => req(`/api/staff/tickets/${id}/accept`, { method: 'POST', body: { assignee_id } }),
  assignTicket: (id, assignee_id) => req(`/api/staff/tickets/${id}/assign`, { method: 'POST', body: { assignee_id } }),
  startTicket: (id) => req(`/api/staff/tickets/${id}/start`, { method: 'POST', body: {} }),
  finishTicket: (id, data) => req(`/api/staff/tickets/${id}/finish`, { method: 'POST', body: data }),
  closeTicket: (id, reason) => req(`/api/staff/tickets/${id}/close`, { method: 'POST', body: { reason } }),
  overview: () => req('/api/staff/tickets/stats/overview'),
  board: () => req('/api/staff/tickets/board'),
  dutyWeek: (week_start) => req('/api/staff/duty', { params: { week_start } }),
  saveDutyWeek: (data) => req('/api/staff/duty/week', { method: 'PUT', body: data }),
  addDutyAdjust: (data) => req('/api/staff/duty/adjustments', { method: 'POST', body: data }),
  deleteDutyAdjust: (id) => req(`/api/staff/duty/adjustments/${id}`, { method: 'DELETE' }),
  manualTicket: (data) => req('/api/staff/tickets/manual', { method: 'POST', body: data }),
  transferTicket: (id, to_staff_id, note) =>
    req(`/api/staff/tickets/${id}/transfer`, { method: 'POST', body: { to_staff_id, note } }),
  pendingTransfers: () => req('/api/staff/tickets/transfers/pending'),
  acceptTransfer: (id) => req(`/api/staff/tickets/transfers/${id}/accept`, { method: 'POST', body: {} }),
  rejectTransfer: (id) => req(`/api/staff/tickets/transfers/${id}/reject`, { method: 'POST', body: {} }),

  // ---------- 字典 / 分类 ----------
  dicts: (kind) => req(`/api/staff/dicts/${kind}`),
  createDict: (kind, data) => req(`/api/staff/dicts/${kind}`, { method: 'POST', body: data }),
  updateDict: (kind, id, data) => req(`/api/staff/dicts/${kind}/${id}`, { method: 'PUT', body: data }),
  deleteDict: (kind, id) => req(`/api/staff/dicts/${kind}/${id}`, { method: 'DELETE' }),
  categories: () => req('/api/staff/categories'),
  createCategory: (data) => req('/api/staff/categories', { method: 'POST', body: data }),
  updateCategory: (id, data) => req(`/api/staff/categories/${id}`, { method: 'PUT', body: data }),
  deleteCategory: (id) => req(`/api/staff/categories/${id}`, { method: 'DELETE' }),

  // ---------- 物资 ----------
  materials: (params) => req('/api/staff/materials', { params }),
  importMaterials: (content) => req('/api/staff/materials/import', { method: 'POST', body: { content } }),
  materialOptions: () => req('/api/staff/materials/options'),
  createMaterial: (data) => req('/api/staff/materials', { method: 'POST', body: data }),
  updateMaterial: (id, data) => req(`/api/staff/materials/${id}`, { method: 'PUT', body: data }),
  inbound: (id, data) => req(`/api/staff/materials/${id}/inbound`, { method: 'POST', body: data }),
  outbound: (id, data) => req(`/api/staff/materials/${id}/outbound`, { method: 'POST', body: data }),
  stockLogs: (params) => req('/api/staff/stock-logs', { params }),

  // ---------- 设备台账 ----------
  assets: (params) => req('/api/staff/assets', { params }),
  assetMeta: () => req('/api/staff/assets/meta'),
  createAsset: (data) => req('/api/staff/assets', { method: 'POST', body: data }),
  updateAsset: (id, data) => req(`/api/staff/assets/${id}`, { method: 'PUT', body: data }),
  deleteAsset: (id) => req(`/api/staff/assets/${id}`, { method: 'DELETE' }),
  revealAssetPassword: (id) => req(`/api/staff/assets/${id}/reveal-password`, { method: 'POST', body: {} }),
  importAssets: (data) => req('/api/staff/assets/import', { method: 'POST', body: data }),

  // ---------- 房间 / 二维码 ----------
  rooms: (params) => req('/api/staff/rooms', { params }),
  createRoom: (data) => req('/api/staff/rooms', { method: 'POST', body: data }),
  updateRoom: (id, data) => req(`/api/staff/rooms/${id}`, { method: 'PUT', body: data }),
  deleteRoom: (id) => req(`/api/staff/rooms/${id}`, { method: 'DELETE' }),
  regenQr: (id) => req(`/api/staff/rooms/${id}/regen-qr`, { method: 'POST' }),
}
