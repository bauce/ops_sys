<template>
  <div class="board">
    <header class="board-head">
      <div class="board-brand">
        <div class="board-mark">运</div>
        <div>
          <div class="board-title">报障实时看板</div>
          <div class="board-sub">信息化运维 · 受理中心</div>
        </div>
      </div>

      <div class="board-clock">
        <div class="clock">{{ clock }}</div>
        <div class="date">{{ dateText }}</div>
      </div>

      <div class="board-actions">
        <button class="ghost-btn" :class="{ on: voiceOn }" @click="toggleVoice">
          {{ voiceOn ? '🔊 语音提醒已开' : '🔇 开启语音提醒' }}
        </button>
        <button class="ghost-btn" @click="toggleFullscreen">⛶ 全屏</button>
        <button class="ghost-btn" @click="$router.push('/admin')">返回后台</button>
      </div>
    </header>

    <div class="board-strip">
      <div class="duty-inline">
        <span class="strip-label">今日值班</span>
        <template v-if="duty.length">
          <span v-for="(d, i) in duty" :key="i" class="duty-chip">
            <b>{{ d.kind === 'temp' ? '临时' : '本周' }}</b> {{ d.name }}
            <span v-if="d.time" class="duty-phone">{{ d.time }}</span>
            <span v-else-if="d.phone" class="duty-phone">{{ d.phone }}</span>
          </span>
        </template>
        <span v-else class="duty-empty">未排班（可在后台「值班排班」中安排）</span>
      </div>
      <div v-if="overdue.length" class="overdue-inline">⚠ {{ overdue.length }} 单超时</div>
    </div>

    <section class="stat-row">
      <button class="big-stat accent" :class="{ active: view === 'pending' }" @click="setView('pending')">
        <div class="label">待受理</div>
        <div class="num">{{ stats.pending || 0 }}</div>
      </button>
      <button class="big-stat" :class="{ active: view === 'today' }" @click="setView('today')">
        <div class="label">今日新增</div>
        <div class="num">{{ stats.today_new || 0 }}</div>
      </button>
      <button class="big-stat" :class="{ active: view === 'processing' }" @click="setView('processing')">
        <div class="label">处理中</div>
        <div class="num">{{ stats.processing || 0 }}</div>
      </button>
      <button class="big-stat" :class="{ active: view === 'pending_confirm' }" @click="setView('pending_confirm')">
        <div class="label">待确认</div>
        <div class="num">{{ stats.pending_confirm || 0 }}</div>
      </button>
      <button class="big-stat" :class="{ danger: overdue.length, active: view === 'overdue' }" @click="setView('overdue')">
        <div class="label">超时工单</div>
        <div class="num">{{ overdue.length }}</div>
      </button>
    </section>

    <main class="board-main">
      <div class="list-head">
        <span>{{ viewTitle }}</span>
        <div class="head-right">
          <span class="hint">每 8 秒自动刷新 · {{ lastUpdated || '—' }}</span>
          <button class="ghost-btn all-btn" :class="{ on: view === 'all' }" @click="setView('all')">全部工单</button>
        </div>
      </div>

      <div v-if="!viewTickets.length" class="board-empty">
        <div class="empty-icon">✓</div>
        <div class="empty-text">{{ emptyText }}</div>
        <div class="empty-sub">新报障到达时会自动语音播报</div>
      </div>

      <div v-if="viewTickets.length" class="ticket-grid">
        <div
          v-for="t in viewTickets"
          :key="t.id"
          class="ticket-card"
          :class="{ fresh: freshIds.has(t.id), overdue: t.overdue_reason }"
        >
          <div class="ticket-top">
            <span class="ticket-loc">{{ t.location }}</span>
            <span v-if="t.overdue_reason" class="badge-overdue">{{ t.overdue_reason }}</span>
            <span v-else class="badge-status">{{ t.status_text }}</span>
          </div>
          <div class="ticket-device">{{ t.device }}</div>
          <div class="ticket-meta">
            <span>{{ t.fault_type }}</span>
            <span class="dot">·</span>
            <span>{{ t.assignee_name || '未指派' }}</span>
            <span class="dot">·</span>
            <span>{{ ago(t.wait_minutes) }}</span>
          </div>
          <div v-if="t.status === 'pending'" class="ticket-expect" :class="{ urgent: t.expect_time === '立即上门' }">
            {{ t.expect_time || '立即上门' }}
          </div>
          <div v-else class="ticket-meta" style="margin-top: 6px">
            <span>{{ t.contact_name }} {{ t.contact_phone }}</span>
          </div>
        </div>
      </div>
    </main>

    <transition name="alert">
      <div v-if="alert" class="new-alert">
        <div class="alert-badge">新报障</div>
        <div class="alert-body">
          <div class="alert-loc">{{ alert.location }}</div>
          <div class="alert-device">{{ alert.device }} · {{ alert.fault_type }}</div>
        </div>
        <div class="alert-time">{{ alert.time }}</div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import { ensureAuth } from '../store'

const clock = ref('')
const dateText = ref('')
const stats = reactive({})
const pending = ref([])
const overdue = ref([])
const duty = ref([])
const alert = ref(null)
const voiceOn = ref(localStorage.getItem('ops_board_voice') === '1')
const lastUpdated = ref('')
const freshIds = ref(new Set())
const view = ref('pending')
const allTickets = ref([])

let known = new Set()
let initialized = false
let timer = null
let clockTimer = null
let alertTimer = null
let audioCtx = null

onMounted(async () => {
  const staff = await ensureAuth()
  if (!staff) {
    window.location.href = '/login'
    return
  }
  tickClock()
  clockTimer = setInterval(tickClock, 1000)
  await refresh()
  timer = setInterval(refresh, 8000)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  clearInterval(clockTimer)
  clearTimeout(alertTimer)
  if (window.speechSynthesis) window.speechSynthesis.cancel()
})

function tickClock() {
  const d = new Date()
  clock.value = [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, '0'))
    .join(':')
  dateText.value = d.toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
  })
}

const viewTitle = computed(() => ({
  pending: '待受理工单',
  today: '今日新增工单',
  processing: '处理中工单',
  pending_confirm: '待确认工单',
  overdue: '超时工单',
  all: '全部工单',
}[view.value] || '工单'))

const emptyText = computed(() => ({
  pending: '当前没有待受理工单',
  today: '今天还没有新增工单',
  processing: '当前没有处理中的工单',
  pending_confirm: '当前没有待确认的工单',
  overdue: '当前没有超时工单',
  all: '还没有工单',
}[view.value] || '暂无工单'))

function localToday() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const viewTickets = computed(() => {
  if (view.value === 'pending') return pending.value
  if (view.value === 'overdue') return overdue.value
  if (view.value === 'today') {
    const day = localToday()
    return allTickets.value.filter((t) => (t.created_at || '').slice(0, 10) === day)
  }
  if (view.value === 'processing') return allTickets.value.filter((t) => ['accepted', 'processing'].includes(t.status))
  if (view.value === 'pending_confirm') return allTickets.value.filter((t) => t.status === 'pending_confirm')
  return allTickets.value
})

function setView(next) {
  view.value = next
}

function ago(minutes) {
  const m = Number(minutes || 0)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m} 分钟前`
  return `${Math.floor(m / 60)} 小时前`
}

async function refresh() {
  try {
    const data = await api.board()
    Object.assign(stats, data.stats)
    const items = data.pending
    if (initialized) {
      const newOnes = items.filter((t) => !known.has(t.id))
      if (newOnes.length) {
        triggerAlert(newOnes[0])
        freshIds.value = new Set(newOnes.map((t) => t.id))
        setTimeout(() => { freshIds.value = new Set() }, 30000)
      }
    }
    pending.value = items
    overdue.value = data.overdue
    allTickets.value = data.tickets || []
    duty.value = data.duty || []
    known = new Set(items.map((t) => t.id))
    initialized = true
    const d = new Date()
    lastUpdated.value = [d.getHours(), d.getMinutes(), d.getSeconds()]
      .map((n) => String(n).padStart(2, '0'))
      .join(':')
  } catch (e) {
    if (e.status === 401) window.location.href = '/login'
  }
}

function triggerAlert(ticket) {
  alert.value = {
    location: ticket.location,
    device: ticket.device,
    fault_type: ticket.fault_type,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
  }
  beep()
  speak(`有新的报障工单，地点 ${ticket.location}，设备 ${ticket.device}，故障类型 ${ticket.fault_type}`)
  clearTimeout(alertTimer)
  alertTimer = setTimeout(() => { alert.value = null }, 20000)
}

function beep() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)()
    const now = audioCtx.currentTime
    ;[880, 1174].forEach((freq, i) => {
      const osc = audioCtx.createOscillator()
      const gain = audioCtx.createGain()
      osc.frequency.value = freq
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.0001, now + i * 0.18)
      gain.gain.exponentialRampToValueAtTime(0.25, now + i * 0.18 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.18 + 0.16)
      osc.connect(gain).connect(audioCtx.destination)
      osc.start(now + i * 0.18)
      osc.stop(now + i * 0.18 + 0.2)
    })
  } catch (e) {
    /* 浏览器不支持时忽略 */
  }
}

function speak(text) {
  if (!voiceOn.value || !window.speechSynthesis) return
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = 'zh-CN'
  utter.rate = 0.95
  utter.volume = 1
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utter)
}

function toggleVoice() {
  voiceOn.value = !voiceOn.value
  localStorage.setItem('ops_board_voice', voiceOn.value ? '1' : '0')
  if (voiceOn.value) {
    beep()
    speak('语音提醒已开启')
    ElMessage.success('语音提醒已开启')
  } else if (window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.().catch(() => {})
  } else {
    document.exitFullscreen?.()
  }
}
</script>

<style scoped>
.board {
  min-height: 100vh;
  background: radial-gradient(1400px 700px at 15% -10%, #17305c 0%, #0d1729 55%, #080e19 100%);
  color: #e8eefc;
  padding: 20px 30px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.board-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.board-mark {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #4f8cff, #2f6feb);
  display: grid;
  place-items: center;
  font-size: 20px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(47, 111, 235, 0.45);
}

.board-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
}

.board-sub {
  font-size: 12.5px;
  color: #7f92b4;
  letter-spacing: 2px;
}

.board-clock {
  text-align: center;
}

.clock {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 38px;
  font-weight: 600;
  letter-spacing: 3px;
  color: #cfe0ff;
  line-height: 1.1;
}

.date {
  font-size: 13px;
  color: #7f92b4;
}

.board-actions {
  display: flex;
  gap: 10px;
}

.ghost-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(140, 170, 220, 0.25);
  color: #c7d6f2;
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.16s;
  font-family: inherit;
}

.ghost-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.ghost-btn.on {
  background: rgba(52, 168, 83, 0.18);
  border-color: rgba(52, 168, 83, 0.5);
  color: #7ee2a8;
}

.board-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(120, 155, 210, 0.16);
  border-radius: 12px;
  padding: 8px 16px;
  font-size: 13px;
  min-height: 42px;
}

.duty-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.strip-label {
  color: #7f92b4;
  letter-spacing: 1px;
}

.duty-chip {
  background: rgba(90, 144, 255, 0.12);
  border: 1px solid rgba(90, 144, 255, 0.3);
  border-radius: 999px;
  padding: 3px 12px;
  color: #b9cdf0;
}

.duty-chip b {
  color: #9dc0ff;
  font-weight: 600;
  margin-right: 4px;
}

.duty-phone {
  color: #7f92b4;
  margin-left: 4px;
  font-size: 12px;
}

.duty-empty {
  color: #6b7f9f;
}

.overdue-inline {
  color: #ffb3b3;
  background: rgba(220, 60, 60, 0.14);
  border: 1px solid rgba(220, 80, 80, 0.4);
  padding: 4px 14px;
  border-radius: 999px;
  font-weight: 600;
  white-space: nowrap;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.big-stat {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(120, 155, 210, 0.18);
  border-radius: 14px;
  padding: 12px 20px;
}

.big-stat.accent {
  background: linear-gradient(135deg, rgba(47, 111, 235, 0.35), rgba(79, 140, 255, 0.15));
  border-color: rgba(90, 144, 255, 0.55);
}

.big-stat.danger {
  border-color: rgba(220, 80, 80, 0.55);
  background: linear-gradient(135deg, rgba(220, 60, 60, 0.22), rgba(220, 60, 60, 0.06));
}

.big-stat .label {
  font-size: 13px;
  color: #8ea3c7;
  letter-spacing: 1px;
}

.big-stat .num {
  font-size: 34px;
  font-weight: 700;
  line-height: 1.2;
  font-family: 'SF Mono', Menlo, monospace;
}

.big-stat.accent .num {
  color: #9dc0ff;
}

.big-stat.danger .num {
  color: #ff9b9b;
}

.board-main {
  flex: 1;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(120, 155, 210, 0.15);
  border-radius: 16px;
  padding: 14px 18px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #cfe0ff;
  padding: 2px 4px 10px;
}

.list-head .hint {
  font-size: 12px;
  color: #6b7f9f;
  font-weight: 400;
  letter-spacing: 0;
}

.overdue-block {
  margin-bottom: 12px;
}

.block-title {
  font-size: 13px;
  color: #8ea3c7;
  letter-spacing: 1px;
  margin: 2px 2px 8px;
}

.block-title.warn {
  color: #ff9b9b;
}

.ticket-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(370px, 1fr));
  gap: 12px;
  padding: 2px;
}

.ticket-card {
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(120, 155, 210, 0.2);
  border-radius: 14px;
  padding: 14px 18px;
  transition: all 0.3s;
}

.ticket-card.fresh {
  border-color: rgba(90, 200, 140, 0.7);
  box-shadow: 0 0 0 2px rgba(90, 200, 140, 0.25), 0 10px 30px rgba(40, 160, 100, 0.18);
}

.ticket-card.overdue {
  border-color: rgba(220, 80, 80, 0.55);
  background: linear-gradient(160deg, rgba(220, 60, 60, 0.14), rgba(255, 255, 255, 0.03));
}

.ticket-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.ticket-loc {
  font-size: 19px;
  font-weight: 700;
  color: #eaf1ff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ticket-time {
  font-size: 12.5px;
  color: #7f92b4;
  white-space: nowrap;
}

.badge-overdue {
  font-size: 12px;
  color: #ffd0d0;
  background: rgba(220, 60, 60, 0.25);
  border: 1px solid rgba(220, 80, 80, 0.5);
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.ticket-device {
  font-size: 15.5px;
  color: #b9cdf0;
  margin-top: 5px;
}

.ticket-meta {
  font-size: 13px;
  color: #7f92b4;
  margin-top: 4px;
}

.ticket-meta .dot {
  margin: 0 6px;
}

.ticket-expect {
  display: inline-block;
  margin-top: 9px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(90, 144, 255, 0.15);
  border: 1px solid rgba(90, 144, 255, 0.35);
  color: #9dc0ff;
  font-size: 12.5px;
}

.ticket-expect.urgent {
  background: rgba(230, 162, 60, 0.16);
  border-color: rgba(230, 162, 60, 0.45);
  color: #f0c274;
}

.board-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #6b7f9f;
}

.empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 2px solid rgba(90, 200, 140, 0.4);
  color: #5ac88c;
  display: grid;
  place-items: center;
  font-size: 28px;
}

.empty-text {
  font-size: 20px;
  color: #9db3d6;
}

.empty-sub {
  font-size: 13px;
}

.new-alert {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(135deg, #2f6feb, #5a90ff);
  color: #fff;
  padding: 14px 24px;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(30, 90, 220, 0.5);
  z-index: 50;
  min-width: 520px;
}

.alert-badge {
  background: rgba(255, 255, 255, 0.22);
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
}

.alert-loc {
  font-size: 19px;
  font-weight: 700;
}

.alert-device {
  font-size: 13px;
  opacity: 0.9;
}

.alert-time {
  margin-left: auto;
  font-size: 13px;
  opacity: 0.8;
}

.alert-enter-active,
.alert-leave-active {
  transition: all 0.35s ease;
}

.alert-enter-from,
.alert-leave-to {
  opacity: 0;
  transform: translate(-50%, -20px);
}

@media (max-width: 1100px) {
  .stat-row {
    grid-template-columns: repeat(3, 1fr);
  }
  .board-clock {
    display: none;
  }
  .new-alert {
    min-width: auto;
    width: calc(100% - 40px);
  }
}

.big-stat {
  font-family: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s, outline-color 0.15s;
}
.big-stat:hover {
  transform: translateY(-2px);
}
.big-stat.active {
  outline: 2px solid rgba(120, 170, 255, 0.9);
  outline-offset: 2px;
}
.head-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.all-btn {
  padding: 6px 14px;
  font-size: 13px;
}
.badge-status {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 999px;
  color: #bcd0f4;
  background: rgba(80, 130, 220, 0.18);
}
</style>
