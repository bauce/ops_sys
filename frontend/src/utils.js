export const STATUS = {
  pending: { text: '待受理', type: 'warning', color: '#e6a23c' },
  accepted: { text: '已受理', type: 'primary', color: '#409eff' },
  processing: { text: '处理中', type: 'primary', color: '#409eff' },
  pending_confirm: { text: '待确认', type: 'warning', color: '#b88230' },
  confirmed: { text: '已完成', type: 'success', color: '#67c23a' },
  cancelled: { text: '已取消', type: 'info', color: '#909399' },
}

export const ROLE_TEXT = {
  admin: '系统管理员',
  dispatcher: '报障受理员',
  engineer: '运维工程师',
}

export function statusMeta(status) {
  return STATUS[status] || { text: status, type: 'info', color: '#909399' }
}

export function fmtTime(value) {
  if (!value) return '—'
  return String(value).replace('T', ' ').slice(0, 16)
}

export function shortTime(value) {
  if (!value) return '—'
  const s = String(value).replace('T', ' ')
  return s.slice(5, 16)
}

export function money(n) {
  return Number(n || 0).toFixed(2)
}

export function hasRole(staff, role) {
  if (!staff) return false
  const roles = staff.roles && staff.roles.length ? staff.roles : [staff.role]
  return roles.includes(role)
}

export function isDispatcher(staff) {
  return hasRole(staff, 'admin') || hasRole(staff, 'dispatcher')
}

/** 值班中的工程师也临时拥有受理派单权限 */
export function canDispatch(staff) {
  return isDispatcher(staff) || (!!staff && !!staff.on_duty && hasRole(staff, 'engineer'))
}
