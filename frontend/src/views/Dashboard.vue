<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">工作台</h2>
        <div class="page-sub">今天 {{ today }} · 待受理 {{ stats.counts.pending || 0 }} 单</div>
      </div>
      <div class="gap-8">
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <el-button v-if="canDispatch" :icon="Phone" @click="openManual">电话报障</el-button>
        <el-button type="primary" :icon="Plus" @click="$router.push('/admin/rooms')">生成二维码</el-button>
      </div>
    </div>

    <el-alert
      v-if="stats.low_stock"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 14px; border-radius: 10px"
      :title="`有 ${stats.low_stock} 种物资低于预警库存，请及时补充`"
    >
      <template #default>
        <el-button link type="warning" @click="$router.push('/admin/materials')">去查看</el-button>
      </template>
    </el-alert>

    <div class="stat-grid">
      <div class="stat-card accent" style="cursor: pointer" @click="$router.push('/admin/tickets')">
        <div class="stat-label">待受理</div>
        <div class="stat-value">{{ stats.counts.pending || 0 }}<small>单</small></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">处理中</div>
        <div class="stat-value">{{ (stats.counts.accepted || 0) + (stats.counts.processing || 0) }}<small>单</small></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">待用户确认</div>
        <div class="stat-value">{{ stats.counts.pending_confirm || 0 }}<small>单</small></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">今日新增</div>
        <div class="stat-value">{{ stats.today_new }}<small>单</small></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">近 7 天完成</div>
        <div class="stat-value">{{ stats.week_done }}<small>单</small></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">平均处理时长</div>
        <div class="stat-value">{{ stats.avg_hours }}<small>小时</small></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">服务评分</div>
        <div class="stat-value">{{ stats.avg_rating || '—' }}<small>/ 5</small></div>
      </div>
    </div>

    <div class="two-col">
      <div class="section-card">
        <div class="card-title">
          <span>待受理工单</span>
          <el-button link type="primary" @click="$router.push('/admin/tickets')">全部工单 →</el-button>
        </div>
        <el-table :data="pending" size="default" @row-click="goDetail" style="cursor: pointer">
          <el-table-column prop="code" label="单号" width="134">
            <template #default="{ row }"><span class="mono" style="font-size: 12.5px">{{ row.code }}</span></template>
          </el-table-column>
          <el-table-column prop="location" label="地点" show-overflow-tooltip min-width="130" />
          <el-table-column prop="device" label="设备" show-overflow-tooltip min-width="100" />
          <el-table-column prop="contact_name" label="报障人" width="90" />
          <el-table-column label="期望上门" width="122">
            <template #default="{ row }">
              <span style="font-size: 12px; color: #2f6feb; white-space: nowrap">{{ row.expect_time || '立即上门' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="提交时间" width="104">
            <template #default="{ row }"><span class="muted" style="font-size: 12px; white-space: nowrap">{{ shortTime(row.created_at) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="76" align="center">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click.stop="openAccept(row)">受理</el-button>
            </template>
          </el-table-column>
          <template #empty><div class="empty-hint">暂无待受理工单</div></template>
        </el-table>
      </div>

      <div>
        <div class="section-card">
          <div class="card-title">近 30 天报障最多的地点</div>
          <div v-if="!stats.top_rooms?.length" class="empty-hint">暂无数据</div>
          <div v-for="(r, i) in stats.top_rooms" :key="i" class="rank-row">
            <span class="rank-no">{{ i + 1 }}</span>
            <span class="rank-name">{{ r.location }}</span>
            <div class="rank-bar">
              <div class="rank-bar-inner" :style="{ width: percent(r.c, maxRoom) + '%' }"></div>
            </div>
            <span class="muted rank-count">{{ r.c }} 次</span>
          </div>
        </div>

        <div class="section-card">
          <div class="card-title">故障类型分布</div>
          <div v-if="!stats.fault_types?.length" class="empty-hint">暂无数据</div>
          <div v-for="(f, i) in stats.fault_types" :key="i" class="rank-row">
            <span class="rank-name" style="flex: 1">{{ f.fault_type }}</span>
            <el-progress
              :percentage="percent(f.c, maxFault)"
              :show-text="false"
              :stroke-width="6"
              style="width: 90px"
              color="#67c23a"
            />
            <span class="muted" style="font-size: 12px; margin-left: 8px">{{ f.c }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="manualVisible" title="电话报障代录" width="560px" align-center>
      <el-form label-position="top">
        <el-form-item label="报障地点" required>
          <el-autocomplete
            v-model="manual.location"
            :fetch-suggestions="suggestRooms"
            placeholder="选择房间或直接输入地点"
            style="width: 100%"
            @select="onPickRoom"
            @input="manual.room_id = null"
          >
            <template #default="{ item }">
              <span>{{ item.value }}</span>
            </template>
          </el-autocomplete>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="故障设备" required>
              <el-input v-model="manual.device" placeholder="如 打印机" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="故障类型" required>
              <el-select v-model="manual.fault_type" placeholder="请选择" style="width: 100%">
                <el-option v-for="t in faultTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="故障描述">
          <el-input v-model="manual.description" type="textarea" :rows="2" placeholder="用户电话中描述的现象" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="联系人" required>
              <el-input v-model="manual.contact_name" placeholder="来电人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话" required>
              <el-input v-model="manual.contact_phone" placeholder="来电号码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="期待上门时间">
              <div style="width: 100%">
                <el-select v-model="manual.expect_mode" style="width: 100%">
                  <el-option label="立即上门" value="asap" />
                  <el-option label="指定时间" value="custom" />
                </el-select>
                <el-date-picker
                  v-if="manual.expect_mode === 'custom'"
                  v-model="manual.expect_time"
                  type="datetime"
                  placeholder="选择时间点"
                  format="YYYY-MM-DD HH:mm"
                  :disabled-date="disabledManualDate"
                  style="width: 100%; margin-top: 8px"
                />
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="指派处理人（可选，选中即派单）">
              <el-select v-model="manual.assignee_id" placeholder="稍后派单" clearable style="width: 100%">
                <el-option v-for="u in engineers" :key="u.id" :label="`${u.name}（${u.role_text}）`" :value="u.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <div class="muted" style="font-size: 12px">
          选择处理人后会立即派单并发送邮件提醒（需在系统设置中配置邮件）
        </div>
      </el-form>
      <template #footer>
        <el-button @click="manualVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doManual">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="acceptVisible" title="受理工单" width="420px" align-center>
      <div v-if="accepting" class="muted" style="font-size: 13px; margin-bottom: 14px">
        {{ accepting.code }} · {{ accepting.location }} · {{ accepting.device }}
      </div>
      <el-form label-position="top">
        <el-form-item label="指派上门/处理人员">
          <el-select v-model="assigneeId" placeholder="可不指派，稍后再派" clearable style="width: 100%">
            <el-option v-for="u in engineers" :key="u.id" :label="`${u.name}（${u.role_text}）`" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="acceptVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doAccept">确认受理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Phone, Plus, Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth } from '../store'
import { canDispatch as canDispatchRole, shortTime } from '../utils'

const router = useRouter()
const stats = ref({
  counts: {}, today_new: 0, week_done: 0, avg_hours: 0, avg_rating: 0,
  low_stock: 0, top_rooms: [], fault_types: [],
})
const pending = ref([])
const engineers = ref([])
const faultTypes = ref([])
const rooms = ref([])
const canDispatch = computed(() => canDispatchRole(auth.staff))
const manualVisible = ref(false)
const manual = reactive({
  location: '', room_id: null, device: '', fault_type: '', description: '',
  contact_name: '', contact_phone: '', expect_mode: 'asap', expect_time: null,
  assignee_id: null,
})
const acceptVisible = ref(false)
const accepting = ref(null)
const assigneeId = ref(null)
const submitting = ref(false)

const today = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long',
})
const maxRoom = computed(() => Math.max(1, ...(stats.value.top_rooms || []).map((r) => r.c)))
const maxFault = computed(() => Math.max(1, ...(stats.value.fault_types || []).map((r) => r.c)))

function percent(v, max) {
  return Math.round((v / max) * 100)
}

onMounted(() => {
  load()
  loadMeta()
})

async function load() {
  try {
    const [ov, list, users] = await Promise.all([
      api.overview(),
      api.tickets({ status: 'pending', page_size: 8 }),
      api.users(),
    ])
    stats.value = ov
    pending.value = list.items
    engineers.value = users.items.filter((u) => u.active && (u.roles || [u.role]).includes('engineer'))
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function goDetail(row) {
  router.push({ path: '/admin/tickets', query: { open: row.id } })
}

async function loadMeta() {
  try {
    const meta = await api.meta()
    faultTypes.value = meta.fault_types
    rooms.value = meta.rooms
  } catch (e) {
    /* ignore */
  }
}

function suggestRooms(query, cb) {
  const q = (query || '').toLowerCase()
  const list = rooms.value
    .filter((r) => !q || r.location.toLowerCase().includes(q))
    .map((r) => ({ value: r.location, id: r.id }))
  cb(list.slice(0, 10))
}

function onPickRoom(item) {
  manual.room_id = item.id
  manual.location = item.value
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

function formatDateTime(value) {
  if (!value) return ''
  const d = new Date(value)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

function defaultExpectTime() {
  const now = new Date()
  const d = new Date(now)
  d.setSeconds(0, 0)
  const m = d.getMinutes()
  if (m < 30) d.setMinutes(30)
  else { d.setHours(d.getHours() + 1); d.setMinutes(0) }
  if (d <= now) d.setMinutes(d.getMinutes() + 30)
  if (d.getDate() !== now.getDate()) {
    const t = new Date(now)
    t.setDate(t.getDate() + 1)
    t.setHours(9, 0, 0, 0)
    return t
  }
  return d
}

function disabledManualDate(date) {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  return date < start
}

watch(
  () => manual.expect_mode,
  (mode) => {
    if (mode === 'custom' && !manual.expect_time) {
      manual.expect_time = defaultExpectTime()
    }
  }
)

function openManual() {
  if (!faultTypes.value.length) loadMeta()
  Object.assign(manual, {
    location: '', room_id: null, device: '', fault_type: '', description: '',
    contact_name: '', contact_phone: '', expect_mode: 'asap', expect_time: null,
    assignee_id: null,
  })
  manualVisible.value = true
}

async function doManual() {
  if (!manual.location || !manual.device || !manual.fault_type || !manual.contact_name || !manual.contact_phone) {
    ElMessage.warning('请填写地点、设备、故障类型、联系人和电话')
    return
  }
  if (manual.expect_mode === 'custom') {
    if (!manual.expect_time) {
      ElMessage.warning('请选择指定的上门时间')
      return
    }
    if (new Date(manual.expect_time).getTime() < Date.now() - 60000) {
      ElMessage.warning('上门时间不能早于当前时间')
      return
    }
  }
  submitting.value = true
  try {
    const res = await api.manualTicket({
      room_id: manual.room_id,
      location_text: manual.location,
      device: manual.device,
      fault_type: manual.fault_type,
      description: manual.description,
      contact_name: manual.contact_name,
      contact_phone: manual.contact_phone,
      expect_time: manual.expect_mode === 'asap'
        ? '立即上门'
        : (formatDateTime(manual.expect_time) || '立即上门'),
      assignee_id: manual.assignee_id || undefined,
    })
    ElMessage.success(`已代录 ${res.code}${res.assignee_name ? '，已派给 ' + res.assignee_name : ''}`)
    manualVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

function openAccept(row) {
  accepting.value = row
  assigneeId.value = null
  acceptVisible.value = true
}

async function doAccept() {
  submitting.value = true
  try {
    await api.acceptTicket(accepting.value.id, assigneeId.value || undefined)
    ElMessage.success('已受理')
    acceptVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.rank-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}
.rank-count {
  font-size: 12px;
  white-space: nowrap;
  flex: 0 0 auto;
}
.rank-no {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: #f0f4fb;
  color: #7b8aa4;
  font-size: 11px;
  display: grid;
  place-items: center;
}
.rank-name {
  color: var(--ink-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 130px;
}
.rank-bar {
  flex: 1;
  height: 6px;
  background: #eef2f8;
  border-radius: 999px;
  margin: 0 8px;
  overflow: hidden;
  min-width: 36px;
}
.rank-bar-inner {
  height: 100%;
  background: linear-gradient(90deg, #4f8cff, #2f6feb);
  border-radius: 999px;
  min-width: 4px;
  transition: width 0.3s;
}
</style>
