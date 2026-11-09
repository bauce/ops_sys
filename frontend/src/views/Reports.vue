<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">运维报表</h2>
        <div class="page-sub">{{ period === 'week' ? '周报' : '月报' }} · {{ data.label || '加载中' }}</div>
      </div>
      <div class="gap-8">
        <el-radio-group v-model="period" @change="load">
          <el-radio-button label="week">周报</el-radio-button>
          <el-radio-button label="month">月报</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="anchor"
          type="date"
          value-format="YYYY-MM-DD"
          :clearable="false"
          style="width: 150px"
          @change="load"
        />
        <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        <el-button :icon="Download" @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>

    <div class="kpi-grid" v-loading="loading">
      <div class="kpi-card">
        <div class="kpi-label">新增工单</div>
        <div class="kpi-value">{{ s.created }}<small>单</small></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已完成</div>
        <div class="kpi-value">{{ s.confirmed }}<small>单</small></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">平均响应</div>
        <div class="kpi-value">{{ s.avg_response_hours }}<small>小时</small></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">平均修复</div>
        <div class="kpi-value">{{ s.avg_repair_hours }}<small>小时</small></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">服务评分</div>
        <div class="kpi-value">{{ s.avg_rating || '—' }}<small>/ 5</small></div>
      </div>
      <div class="kpi-card warn">
        <div class="kpi-label">超时未受理</div>
        <div class="kpi-value">{{ s.overdue_pending }}<small>单</small></div>
      </div>
    </div>

    <div class="two-col">
      <div class="section-card">
        <div class="card-title">工单状态分布</div>
        <div v-for="row in data.status" :key="row.status" class="bar-row">
          <span class="bar-label">{{ statusText(row.status) }}</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: pct(row.count, maxStatus) + '%' }" /></div>
          <span class="bar-num">{{ row.count }}</span>
        </div>
        <div v-if="!data.status?.length" class="empty-hint">本期暂无工单</div>
      </div>

      <div class="section-card">
        <div class="card-title">故障类型 Top 8</div>
        <div v-for="row in data.faults" :key="row.name" class="bar-row">
          <span class="bar-label">{{ row.name }}</span>
          <div class="bar-track"><div class="bar-fill blue" :style="{ width: pct(row.count, maxFault) + '%' }" /></div>
          <span class="bar-num">{{ row.count }}</span>
        </div>
        <div v-if="!data.faults?.length" class="empty-hint">本期暂无故障数据</div>
      </div>
    </div>

    <div class="section-card">
      <div class="card-title">
        <span>每日趋势</span>
        <span class="legend"><i class="dot created" />新增 <i class="dot done" />完成</span>
      </div>
      <div class="trend">
        <div v-for="d in data.trend" :key="d.date" class="trend-col">
          <div class="trend-bars">
            <div class="trend-bar created" :style="{ height: pct(d.created, maxTrend) + '%' }" :title="`新增 ${d.created}`" />
            <div class="trend-bar done" :style="{ height: pct(d.done, maxTrend) + '%' }" :title="`完成 ${d.done}`" />
          </div>
          <div class="trend-date">{{ d.date.slice(5) }}</div>
        </div>
      </div>
    </div>

    <div class="two-col">
      <div class="section-card">
        <div class="card-title">工程师工作量</div>
        <el-table :data="data.engineers" size="small">
          <el-table-column prop="name" label="工程师" min-width="90" />
          <el-table-column prop="assigned" label="接单" width="70" align="center" />
          <el-table-column prop="done" label="完成" width="70" align="center" />
          <el-table-column label="平均修复" width="100" align="right">
            <template #default="{ row }">{{ row.avg_hours }} h</template>
          </el-table-column>
        </el-table>
        <div v-if="!data.engineers?.length" class="empty-hint">本期暂无处理记录</div>
      </div>

      <div class="section-card">
        <div class="card-title">报障房间 Top 8</div>
        <el-table :data="data.rooms" size="small">
          <el-table-column prop="location" label="房间" min-width="160" show-overflow-tooltip />
          <el-table-column label="等级" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" effect="light" :type="row.importance === '核心' ? 'danger' : row.importance === '重要' ? 'warning' : 'info'">
                {{ row.importance }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="count" label="报障" width="70" align="center" />
        </el-table>
        <div v-if="!data.rooms?.length" class="empty-hint">本期暂无报障</div>
      </div>
    </div>

    <div class="section-card">
      <div class="card-title">物资领用统计</div>
      <el-table :data="data.materials" size="small">
        <el-table-column prop="name" label="物资" min-width="160" />
        <el-table-column prop="qty" label="领用数量" width="110" align="center" />
        <el-table-column prop="tickets" label="关联工单" width="110" align="center" />
      </el-table>
      <div v-if="!data.materials?.length" class="empty-hint">本期暂无物资领用</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import { api } from '../api'

const period = ref('week')
const anchor = ref(localDate(new Date()))
const loading = ref(false)
const data = reactive({
  label: '', status: [], faults: [], engineers: [], rooms: [], materials: [], trend: [],
})
const s = computed(() => data.summary || {})

function localDate(d) {
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const statusMap = {
  pending: '待受理', accepted: '已受理', processing: '处理中',
  pending_confirm: '待确认', confirmed: '已完成', cancelled: '已取消',
}
function statusText(v) { return statusMap[v] || v }
function pct(v, max) { return max > 0 ? Math.max(2, Math.round((v / max) * 100)) : 0 }
const maxStatus = computed(() => Math.max(1, ...(data.status || []).map((r) => r.count)))
const maxFault = computed(() => Math.max(1, ...(data.faults || []).map((r) => r.count)))
const maxTrend = computed(() => Math.max(1, ...(data.trend || []).flatMap((d) => [d.created, d.done])))

async function load() {
  loading.value = true
  try {
    const res = await api.reportSummary(period.value, anchor.value)
    Object.assign(data, {
      label: res.label,
      summary: res.summary,
      status: res.status,
      faults: res.faults,
      engineers: res.engineers,
      rooms: res.rooms,
      materials: res.materials,
      trend: res.trend,
    })
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function exportCsv() {
  const rows = [
    ['运维报表', data.label],
    ['指标', '数值'],
    ['新增工单', s.value.created],
    ['已完成', s.value.confirmed],
    ['平均响应(小时)', s.value.avg_response_hours],
    ['平均修复(小时)', s.value.avg_repair_hours],
    ['服务评分', s.value.avg_rating],
    ['超时未受理', s.value.overdue_pending],
    [],
    ['工程师', '接单', '完成', '平均修复(小时)'],
    ...(data.engineers || []).map((r) => [r.name, r.assigned, r.done, r.avg_hours]),
    [],
    ['物资', '领用数量', '关联工单'],
    ...(data.materials || []).map((r) => [r.name, r.qty, r.tickets]),
  ]
  const csv = '\ufeff' + rows.map((r) => r.map((v) => `"${v ?? ''}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `运维${period.value === 'week' ? '周报' : '月报'}-${anchor.value}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.kpi-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
}
.kpi-card.warn .kpi-value { color: #e6a23c; }
.kpi-label { font-size: 12px; color: var(--ink-3); }
.kpi-value { margin-top: 6px; font-size: 26px; font-weight: 700; color: #2f6feb; }
.kpi-value small { margin-left: 3px; font-size: 12px; font-weight: 400; color: var(--ink-3); }
.bar-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; }
.bar-label { width: 92px; flex: 0 0 auto; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { flex: 1; height: 10px; border-radius: 999px; background: #eef2f8; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; background: #f0a23c; }
.bar-fill.blue { background: #2f6feb; }
.bar-num { width: 32px; text-align: right; color: var(--ink-3); font-size: 12px; }
.trend { display: flex; align-items: flex-end; gap: 4px; height: 170px; padding-top: 8px; overflow-x: auto; }
.trend-col { flex: 1 0 22px; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 4px; }
.trend-bars { display: flex; align-items: flex-end; gap: 2px; height: 140px; width: 100%; justify-content: center; }
.trend-bar { width: 7px; min-height: 2px; border-radius: 2px 2px 0 0; }
.trend-bar.created { background: #2f6feb; }
.trend-bar.done { background: #46b37a; }
.trend-date { font-size: 9.5px; color: var(--ink-3); white-space: nowrap; }
.legend { font-size: 11px; color: var(--ink-3); font-weight: 400; display: inline-flex; align-items: center; gap: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: 8px; }
.dot.created { background: #2f6feb; }
.dot.done { background: #46b37a; }
@media (max-width: 1100px) {
  .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
