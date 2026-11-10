<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">工单管理</h2>
        <div class="page-sub">受理、派单、上门处理与结果登记</div>
      </div>
      <div class="gap-8">
        <el-input
          v-model="keyword"
          placeholder="搜索单号 / 设备 / 地点 / 报障人"
          :prefix-icon="Search"
          clearable
          style="width: 260px"
          @keyup.enter="reload"
          @clear="reload"
        />
        <el-checkbox v-model="onlyMine" @change="reload">只看我的</el-checkbox>
        <el-button :icon="Refresh" @click="reload">刷新</el-button>
      </div>
    </div>

    <div class="section-card" style="padding-top: 8px">
      <el-tabs v-model="activeStatus" @tab-change="reload">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="待受理" name="pending" />
        <el-tab-pane label="处理中" name="accepted,processing" />
        <el-tab-pane label="待确认" name="pending_confirm" />
        <el-tab-pane label="已完成" name="confirmed" />
        <el-tab-pane label="已取消" name="cancelled" />
      </el-tabs>

      <el-table class="desktop-ticket-table" :data="items" v-loading="loading" @row-click="openTicket" style="cursor: pointer">
        <el-table-column prop="code" label="单号" width="150">
          <template #default="{ row }"><span class="mono" style="font-size: 12.5px">{{ row.code }}</span></template>
        </el-table-column>
        <el-table-column prop="location" label="报障地点" min-width="150" show-overflow-tooltip />
        <el-table-column label="设备 / 故障" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.device }}</div>
            <div class="muted" style="font-size: 12px">{{ row.fault_type }}</div>
          </template>
        </el-table-column>
        <el-table-column label="报障人" width="120">
          <template #default="{ row }">
            <div>{{ row.contact_name }}</div>
            <div class="muted" style="font-size: 12px">{{ row.contact_phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMeta(row.status).type" size="small" effect="light">
              {{ row.status_text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="期望上门" width="130">
          <template #default="{ row }">
            <span style="font-size: 12.5px" :style="{ color: row.expect_time === '立即上门' ? '#e6a23c' : '#2f6feb' }">
              {{ row.expect_time || '立即上门' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="处理人" width="90">
          <template #default="{ row }">
            <span :class="{ muted: !row.assignee_name }">{{ row.assignee_name || '未指派' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="130">
          <template #default="{ row }">
            <span class="muted" style="font-size: 12.5px">{{ fmtTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openTicket(row)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty><div class="empty-hint">没有符合条件的工单</div></template>
      </el-table>

      <div class="mobile-ticket-list" v-loading="loading">
        <div v-for="row in items" :key="row.id" class="m-ticket-card" @click="openTicket(row)">
          <div class="m-ticket-top">
            <span class="m-ticket-code">{{ row.code }}</span>
            <el-tag :type="statusMeta(row.status).type" size="small" effect="light">{{ row.status_text }}</el-tag>
          </div>
          <div class="m-ticket-device">{{ row.device }}</div>
          <div class="m-ticket-loc">{{ row.location }}</div>
          <div class="m-ticket-tags">
            <el-tag size="small" effect="plain" type="info">{{ row.fault_type }}</el-tag>
            <el-tag v-if="row.expect_time === '立即上门'" size="small" effect="plain" type="warning">立即上门</el-tag>
            <el-tag v-else size="small" effect="plain">{{ row.expect_time || '立即上门' }}</el-tag>
          </div>
          <div class="m-ticket-meta">
            <span>{{ row.contact_name }} · {{ row.contact_phone }}</span>
            <span>{{ row.assignee_name || '未指派' }} · {{ fmtTime(row.created_at) }}</span>
          </div>
        </div>
        <div v-if="!items.length && !loading" class="empty-hint">没有符合条件的工单</div>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 14px">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="loadList"
        />
      </div>
    </div>

    <!-- 工单详情抽屉 -->
    <el-drawer v-model="drawerVisible" size="620px" :with-header="false" destroy-on-close>
      <el-button class="m-detail-close" circle :icon="Close" @click="drawerVisible = false" />
      <div v-if="detail" style="padding: 4px 4px 10px">
        <div class="detail-head">
          <div>
            <div style="font-size: 18px; font-weight: 700">{{ detail.device }}</div>
            <div class="detail-code">{{ detail.code }} · {{ fmtTime(detail.created_at) }}</div>
          </div>
          <div class="gap-8">
            <el-tag v-if="detail.source === 'phone'" type="info" effect="plain" size="large">电话代录</el-tag>
            <el-tag :type="statusMeta(detail.status).type" effect="light" size="large">
              {{ detail.status_text }}
            </el-tag>
          </div>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <div class="k">报障地点</div>
            <div class="v">
              {{ detail.location }}
              <el-tag
                v-if="detail.room_importance && detail.room_importance !== '普通'"
                size="small"
                effect="light"
                :type="detail.room_importance === '核心' ? 'danger' : 'warning'"
                style="margin-left: 6px"
              >{{ detail.room_importance }}</el-tag>
            </div>
          </div>
          <div class="info-item">
            <div class="k">故障类型</div>
            <div class="v">{{ detail.fault_type }}</div>
          </div>
          <div class="info-item">
            <div class="k">报障人</div>
            <div class="v">{{ detail.contact_name }} · {{ detail.contact_phone }}</div>
          </div>
          <div class="info-item">
            <div class="k">处理人</div>
            <div class="v">{{ detail.assignee_name || '未指派' }}</div>
          </div>
          <div class="info-item">
            <div class="k">期望上门时间</div>
            <div class="v" style="color: #2f6feb; font-weight: 600">
              {{ detail.expect_time || '立即上门' }}
            </div>
          </div>
          <div class="info-item">
            <div class="k">受理时间</div>
            <div class="v">{{ fmtTime(detail.accepted_at) }}</div>
          </div>
          <div class="info-item">
            <div class="k">完成时间</div>
            <div class="v">{{ fmtTime(detail.finished_at) }}</div>
          </div>
        </div>

        <template v-if="detail.description">
          <div class="sub-label">故障描述</div>
          <div class="note-box">{{ detail.description }}</div>
        </template>
        <template v-if="detail.photos?.length">
          <div class="sub-label">现场照片</div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap">
            <el-image
              v-for="(p, i) in detail.photos"
              :key="i"
              :src="p"
              :preview-src-list="detail.photos"
              :initial-index="i"
              fit="cover"
              style="width: 110px; height: 110px; border-radius: 8px; border: 1px solid var(--line)"
            />
          </div>
        </template>

        <template v-if="detail.fault_cause">
          <div class="sub-label">故障原因</div>
          <div class="note-box">{{ detail.fault_cause }}</div>
        </template>
        <template v-if="detail.solve_note">
          <div class="sub-label">处理说明</div>
          <div class="note-box">{{ detail.solve_note }}</div>
        </template>

        <template v-if="detail.materials?.length">
          <div class="sub-label">领用物资</div>
          <el-table :data="detail.materials" size="small" border>
            <el-table-column prop="material_name" label="物资" />
            <el-table-column prop="spec" label="规格" show-overflow-tooltip />
            <el-table-column label="数量" width="90" align="center">
              <template #default="{ row }">{{ row.qty }} {{ row.unit }}</template>
            </el-table-column>
          </el-table>
        </template>

        <template v-if="detail.signature">
          <div class="sub-label">报障人签字</div>
          <img
            :src="detail.signature"
            alt="签名"
            style="max-width: 240px; width: 55%; border: 1px solid var(--line); border-radius: 8px; background: #fff"
          />
        </template>

        <template v-if="detail.rating">
          <div class="sub-label">用户评价</div>
          <div class="gap-8">
            <el-rate :model-value="detail.rating" disabled />
            <span class="muted" style="font-size: 12.5px">{{ detail.confirm_comment }}</span>
          </div>
        </template>

        <div class="sub-label">处理进度</div>
        <el-timeline style="padding-left: 2px">
          <el-timeline-item
            v-for="(log, i) in detail.logs"
            :key="i"
            :timestamp="fmtTime(log.created_at)"
            placement="top"
            :color="i === detail.logs.length - 1 ? '#2f6feb' : '#c9d6ea'"
          >
            <div style="font-size: 13px; font-weight: 600">{{ log.action }}</div>
            <div class="muted" style="font-size: 12.5px">
              {{ log.actor }}<span v-if="log.note"> · {{ log.note }}</span>
            </div>
          </el-timeline-item>
        </el-timeline>

        <div class="drawer-actions">
          <template v-if="detail.status === 'pending' && canDispatch">
            <el-button type="primary" @click="openAssign()">受理并派单</el-button>
            <el-button @click="openAssign(true)">仅受理</el-button>
            <el-button type="danger" plain @click="closeVisible = true">关闭工单</el-button>
          </template>
          <template v-else-if="['accepted', 'processing'].includes(detail.status)">
            <el-button v-if="detail.status === 'accepted'" @click="start">开始处理</el-button>
            <el-button type="primary" @click="openFinish">提交处理结果</el-button>
            <el-button v-if="canDispatch" @click="openAssign()">改派</el-button>
            <el-button v-if="canDispatch" type="danger" plain @click="closeVisible = true">关闭工单</el-button>
          </template>
          <div v-else-if="detail.status === 'pending_confirm'" class="muted" style="font-size: 13px">
            ⏳ 已提交处理结果，等待报障人确认
          </div>
        </div>
      </div>
      <el-skeleton v-else :rows="8" animated />
    </el-drawer>

    <!-- 受理 / 派单 -->
    <el-dialog v-model="assignVisible" :title="assignMode === 'accept' ? '受理工单' : '指派处理人'" width="420px" align-center>
      <el-form label-position="top">
        <el-form-item :label="assignMode === 'accept' ? '指派上门/处理人员（可不选，稍后再派）' : '处理人员'">
          <el-select v-model="assigneeId" placeholder="请选择" clearable style="width: 100%">
            <el-option v-for="u in engineers" :key="u.id" :label="`${u.name}（${u.role_text}）`" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doAssign">确定</el-button>
      </template>
    </el-dialog>

    <!-- 提交处理结果 -->
    <el-dialog v-model="finishVisible" title="提交处理结果" width="560px" align-center>
      <el-form label-position="top">
        <el-form-item label="故障原因">
          <el-input v-model="finishForm.fault_cause" placeholder="如：电源适配器损坏" maxlength="200" />
        </el-form-item>
        <el-form-item label="处理说明" required>
          <el-input
            v-model="finishForm.solve_note"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="说明处理过程与结果，提交后由报障人确认"
          />
        </el-form-item>
        <el-form-item label="物资使用情况">
          <div style="width: 100%">
            <el-checkbox v-model="noMaterial" style="margin-bottom: 8px">
              本次维修未使用物资
            </el-checkbox>
            <template v-if="!noMaterial">
            <div v-for="(m, i) in finishForm.materials" :key="i" class="material-row">
              <el-select v-model="m.material_id" filterable placeholder="选择物资" style="flex: 1" @change="onMaterialChange(m)">
                <el-option
                  v-for="opt in materialOptions"
                  :key="opt.id"
                  :label="`${opt.name}${opt.spec ? ' · ' + opt.spec : ''}（库存 ${opt.stock}${opt.unit}）`"
                  :value="opt.id"
                />
              </el-select>
              <el-input-number
                v-model="m.qty"
                :min="materialIsUsage(m.material_id) ? 1 : 0.01"
                :precision="materialIsUsage(m.material_id) ? 0 : undefined"
                :step="1"
                controls-position="right"
                style="width: 130px"
              />
              <el-button :icon="Delete" circle @click="finishForm.materials.splice(i, 1)" />
            </div>
            <el-button :icon="Plus" size="small" @click="addMaterial">添加物资</el-button>
            <span class="muted" style="font-size: 12px; margin-left: 8px">提交后自动扣减库存</span>
            </template>
            <div v-else class="muted" style="font-size: 12px">
              本次不登记领用物资，无需扣减库存
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="finishVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doFinish">提交</el-button>
      </template>
    </el-dialog>

    <!-- 关闭工单 -->
    <el-dialog v-model="closeVisible" title="关闭工单" width="420px" align-center>
      <el-input v-model="closeReason" type="textarea" :rows="3" placeholder="请填写关闭原因，如：重复报障、报障人撤销" maxlength="200" />
      <template #footer>
        <el-button @click="closeVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="doClose">确认关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth } from '../store'
import { canDispatch as canDispatchRole, fmtTime, hasRole, statusMeta } from '../utils'

const route = useRoute()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 15
const loading = ref(false)
const keyword = ref('')
const activeStatus = ref('all')
const onlyMine = ref(false)

const drawerVisible = ref(false)
const detail = ref(null)
const engineers = ref([])
const materialOptions = ref([])
function materialIsUsage(id) {
  return materialOptions.value.find((x) => x.id === id)?.measure_mode === 'usage'
}

const assignVisible = ref(false)
const assignMode = ref('assign')
const assigneeId = ref(null)

const finishVisible = ref(false)
const noMaterial = ref(false)
const finishForm = reactive({ fault_cause: '', solve_note: '', materials: [] })

const closeVisible = ref(false)
const closeReason = ref('')
const submitting = ref(false)

const canDispatch = computed(() => canDispatchRole(auth.staff))
const canHandle = computed(() => {
  if (!detail.value || !auth.staff) return false
  if (hasRole(auth.staff, 'admin') || hasRole(auth.staff, 'dispatcher')) return true
  return detail.value.assignee_id === auth.staff.id
})

onMounted(async () => {
  await Promise.all([loadList(), loadOptions()])
  if (route.query.open) openTicket({ id: Number(route.query.open) })
})

async function loadOptions() {
  try {
    const [users, mats] = await Promise.all([api.users(), api.materialOptions()])
    engineers.value = users.items.filter((u) => u.active && u.role !== 'admin')
    materialOptions.value = mats.items
  } catch (e) {
    /* ignore */
  }
}

async function loadList() {
  loading.value = true
  try {
    const res = await api.tickets({
      status: activeStatus.value === 'all' ? '' : activeStatus.value,
      keyword: keyword.value,
      mine: onlyMine.value ? 1 : 0,
      page: page.value,
      page_size: pageSize,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  loadList()
}

async function openTicket(row) {
  drawerVisible.value = true
  detail.value = null
  try {
    detail.value = await api.ticket(row.id)
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function refreshDetail() {
  if (detail.value) return openTicket({ id: detail.value.id })
}

function openAssign(acceptOnly = false) {
  assignMode.value = 'assign'
  if (detail.value.status === 'pending') assignMode.value = 'accept'
  assigneeId.value = acceptOnly ? null : detail.value.assignee_id || null
  assignVisible.value = true
}

async function doAssign() {
  submitting.value = true
  try {
    if (detail.value.status === 'pending') {
      await api.acceptTicket(detail.value.id, assigneeId.value || undefined)
      ElMessage.success('已受理')
    } else {
      if (!assigneeId.value) {
        ElMessage.warning('请选择处理人员')
        submitting.value = false
        return
      }
      await api.assignTicket(detail.value.id, assigneeId.value)
      ElMessage.success('已改派')
    }
    assignVisible.value = false
    await Promise.all([refreshDetail(), loadList()])
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function start() {
  try {
    await api.startTicket(detail.value.id)
    ElMessage.success('已开始处理')
    await Promise.all([refreshDetail(), loadList()])
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function doClose() {
  if (!closeReason.value.trim()) {
    ElMessage.warning('请填写关闭原因')
    return
  }
  submitting.value = true
  try {
    await api.closeTicket(detail.value.id, closeReason.value)
    ElMessage.success('工单已关闭')
    closeVisible.value = false
    closeReason.value = ''
    await Promise.all([refreshDetail(), loadList()])
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.m-detail-close {
  display: none;
}
@media (max-width: 768px) {
  .m-detail-close {
    display: inline-flex;
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 3000;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--line);
    box-shadow: 0 2px 8px rgba(31, 45, 61, 0.12);
  }
}
.sub-label {
  font-size: 12px;
  color: var(--ink-3);
  margin: 16px 0 6px;
}

.drawer-actions {
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
