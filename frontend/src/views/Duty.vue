<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">值班排班</h2>
        <div class="page-sub">整周固定值班人员（2 人及以上），临时某天某时段可调班</div>
      </div>
      <div class="gap-8">
        <el-button :icon="ArrowLeft" @click="shiftWeek(-7)">上一周</el-button>
        <el-button @click="thisWeek">本周</el-button>
        <el-button :icon="ArrowRight" @click="shiftWeek(7)">下一周</el-button>
      </div>
    </div>

    <div class="week-range">{{ weekStart }} ～ {{ weekEnd }}</div>

    <div class="two-col" style="align-items: start">
      <div class="section-card">
        <div class="card-title">
          <span>本周值班人员</span>
          <span class="muted" style="font-size: 12px">至少 2 人</span>
        </div>
        <div v-if="week.staff.length" class="member-list">
          <div v-for="s in week.staff" :key="s.id" class="member-chip">
            <div class="member-avatar">{{ s.name.slice(0, 1) }}</div>
            <div>
              <div class="member-name">{{ s.name }}</div>
              <div class="member-phone">{{ s.phone || '—' }}</div>
            </div>
          </div>
        </div>
        <div v-else class="muted" style="font-size: 13px; padding: 6px 0 12px">
          本周还没有安排值班人员
        </div>

        <el-form label-position="top" style="margin-top: 12px">
          <el-form-item label="选择值班人员（可多选）">
            <el-select v-model="editStaffIds" multiple filterable placeholder="选择人员" style="width: 100%">
              <el-option
                v-for="u in staffOptions"
                :key="u.id"
                :label="`${u.name}（${u.role_text}）`"
                :value="u.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="editNote" placeholder="如 本周由信息中心值班" maxlength="50" />
          </el-form-item>
          <el-button type="primary" :loading="saving" @click="saveWeek">保存本周值班</el-button>
        </el-form>
      </div>

      <div class="section-card">
        <div class="card-title">
          <span>今日值班（{{ today }}）</span>
          <span class="muted" style="font-size: 12px">大屏顶部会显示</span>
        </div>
        <div v-if="todayItems.length" class="today-list">
          <div v-for="(d, i) in todayItems" :key="i" class="today-item">
            <el-tag size="small" :type="d.kind === 'temp' ? 'warning' : 'primary'" effect="plain">
              {{ d.kind === 'temp' ? '临时' : '本周' }}
            </el-tag>
            <b>{{ d.name }}</b>
            <span class="muted">{{ d.phone }}</span>
            <span v-if="d.time" class="today-time">{{ d.time }}</span>
          </div>
        </div>
        <div v-else class="muted" style="font-size: 13px">今天没有值班安排</div>
      </div>
    </div>

    <div class="section-card" style="margin-top: 16px">
      <div class="card-title">
        <span>临时调班</span>
        <el-button type="primary" size="small" :icon="Plus" @click="openAdjust">新增临时调班</el-button>
      </div>
      <p class="muted" style="font-size: 12.5px; margin-top: -6px">
        用于某一天某个时间段临时换人，例如周三 14:00-17:00 由他人替班；不影响整周固定值班安排。
      </p>
      <el-table class="desktop-table" :data="week.adjustments" size="default">
        <el-table-column prop="adjust_date" label="日期" width="120" />
        <el-table-column label="时间段" width="150">
          <template #default="{ row }">{{ row.start_time }} - {{ row.end_time }}</template>
        </el-table-column>
        <el-table-column label="临时值班人员">
          <template #default="{ row }">
            <el-tag v-for="s in row.staff" :key="s.id" size="small" style="margin-right: 6px">
              {{ s.name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" show-overflow-tooltip />
        <el-table-column label="操作" width="80" align="right">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeAdjust(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><div class="empty-hint">本周没有临时调班</div></template>
      </el-table>

      <div class="m-card-list">
        <div v-for="row in week.adjustments" :key="row.id" class="m-data-card">
          <div class="m-card-head">
            <span class="m-card-title" style="font-size: 14px">{{ row.adjust_date }}</span>
            <span class="muted" style="font-size: 12px">{{ row.start_time }} - {{ row.end_time }}</span>
          </div>
          <div class="m-card-row">
            <span class="label">替班</span>
            <span class="value">
              <el-tag v-for="s in row.staff" :key="s.id" size="small" style="margin-left: 4px">{{ s.name }}</el-tag>
            </span>
          </div>
          <div v-if="row.note" class="m-card-row"><span class="label">备注</span><span class="value">{{ row.note }}</span></div>
          <div class="m-card-actions">
            <el-button size="small" type="danger" plain @click="removeAdjust(row)">删除</el-button>
          </div>
        </div>
        <div v-if="!week.adjustments.length" class="empty-hint">本周没有临时调班</div>
      </div>
    </div>

    <el-dialog v-model="adjustVisible" title="新增临时调班" width="460px" align-center>
      <el-form label-position="top">
        <el-form-item label="调班日期" required>
          <el-date-picker
            v-model="adjustForm.adjust_date"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled-date="outsideWeek"
            style="width: 100%"
          />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="开始时间" required>
              <el-time-picker
                v-model="adjustForm.start_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="如 14:00"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间" required>
              <el-time-picker
                v-model="adjustForm.end_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="如 17:00"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="临时值班人员" required>
          <el-select v-model="adjustForm.staff_ids" multiple filterable placeholder="选择人员" style="width: 100%">
            <el-option
              v-for="u in staffOptions"
              :key="u.id"
              :label="`${u.name}（${u.role_text}）`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="adjustForm.note" placeholder="如 张工外出，由王五替班" maxlength="60" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveAdjust">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Plus } from '@element-plus/icons-vue'
import { api } from '../api'

const saving = ref(false)
const weekStart = ref(localDate(startOfWeek(new Date())))
const week = reactive({ staff: [], note: '', adjustments: [] })
const todayItems = ref([])
const staffOptions = ref([])
const editStaffIds = ref([])
const editNote = ref('')
const adjustVisible = ref(false)
const adjustForm = reactive({ adjust_date: '', start_time: '', end_time: '', staff_ids: [], note: '' })

const today = localDate(new Date())
const weekEnd = computed(() => addDays(weekStart.value, 6))

onMounted(async () => {
  await Promise.all([loadWeek(), loadStaff()])
})

function localDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function parseDate(s) {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function addDays(s, n) {
  const d = parseDate(s)
  d.setDate(d.getDate() + n)
  return localDate(d)
}

function startOfWeek(d) {
  const copy = new Date(d)
  const day = (copy.getDay() + 6) % 7
  copy.setDate(copy.getDate() - day)
  copy.setHours(0, 0, 0, 0)
  return copy
}

async function loadWeek() {
  try {
    const data = await api.dutyWeek(weekStart.value)
    week.staff = data.staff || []
    week.note = data.note || ''
    week.adjustments = data.adjustments || []
    editStaffIds.value = week.staff.map((s) => s.id)
    editNote.value = week.note
    todayItems.value = data.today || []
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadStaff() {
  try {
    const res = await api.users()
    staffOptions.value = res.items.filter((u) => u.active)
  } catch (e) {
    /* ignore */
  }
}

function shiftWeek(days) {
  weekStart.value = addDays(weekStart.value, days)
  loadWeek()
}

function thisWeek() {
  weekStart.value = localDate(startOfWeek(new Date()))
  loadWeek()
}

async function saveWeek() {
  if (editStaffIds.value.length < 2) {
    ElMessage.warning('整周值班至少选择 2 人')
    return
  }
  saving.value = true
  try {
    await api.saveDutyWeek({
      week_start: weekStart.value,
      staff_ids: editStaffIds.value,
      note: editNote.value,
    })
    ElMessage.success('本周值班已保存')
    await loadWeek()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

function outsideWeek(date) {
  const s = localDate(date)
  return s < weekStart.value || s > weekEnd.value
}

function openAdjust() {
  adjustForm.adjust_date = weekStart.value
  adjustForm.start_time = '14:00'
  adjustForm.end_time = '17:00'
  adjustForm.staff_ids = []
  adjustForm.note = ''
  adjustVisible.value = true
}

async function saveAdjust() {
  if (!adjustForm.adjust_date || !adjustForm.start_time || !adjustForm.end_time) {
    ElMessage.warning('请填写日期和时间段')
    return
  }
  if (!adjustForm.staff_ids.length) {
    ElMessage.warning('请选择临时值班人员')
    return
  }
  saving.value = true
  try {
    await api.addDutyAdjust({
      week_start: weekStart.value,
      adjust_date: adjustForm.adjust_date,
      start_time: adjustForm.start_time,
      end_time: adjustForm.end_time,
      staff_ids: adjustForm.staff_ids,
      note: adjustForm.note,
    })
    ElMessage.success('临时调班已保存')
    adjustVisible.value = false
    await loadWeek()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function removeAdjust(row) {
  try {
    await ElMessageBox.confirm(
      `删除 ${row.adjust_date} ${row.start_time}-${row.end_time} 的临时调班？`,
      '删除调班',
      { type: 'warning' }
    )
  } catch (e) {
    return
  }
  try {
    await api.deleteDutyAdjust(row.id)
    ElMessage.success('已删除')
    await loadWeek()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.week-range {
  font-size: 13px;
  color: var(--ink-3);
  margin: -6px 0 12px;
  font-family: 'SF Mono', Menlo, monospace;
}

.member-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 6px 0 10px;
}

.member-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f3f7ff;
  border: 1px solid #dbe7fb;
  border-radius: 12px;
  padding: 9px 14px;
  min-width: 150px;
}

.member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #dbe8ff;
  color: #2f6feb;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 13px;
}

.member-name {
  font-size: 14px;
  font-weight: 600;
}

.member-phone {
  font-size: 12px;
  color: var(--ink-3);
}

.today-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.today-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafd;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
}

.today-time {
  margin-left: auto;
  color: var(--ink-3);
  font-size: 12.5px;
  font-family: 'SF Mono', Menlo, monospace;
}
</style>
