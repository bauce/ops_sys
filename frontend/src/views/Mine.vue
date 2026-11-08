<template>
  <div class="pub-page">
    <div class="pub-topbar">
      <div class="brand">
        <div class="brand-mark">运</div>
        <span>我的报障</span>
      </div>
      <el-button link type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>

    <div class="pub-wrap">
      <div class="pub-card">
        <h3>查询我提交过的报障</h3>
        <p class="pub-hint">
          扫码进入后，输入报障时填写的手机号后四位，就能查看该号码提交过的报障单
        </p>
        <div class="gap-8">
          <el-input
            v-model="tail"
            size="large"
            maxlength="4"
            placeholder="手机号后四位"
            inputmode="numeric"
            clearable
            @keyup.enter="doLookup"
          />
          <el-button type="primary" size="large" :loading="loading" @click="doLookup">查询</el-button>
        </div>
        <div v-if="activeTail" class="tail-note">
          正在查看尾号 <b>{{ activeTail }}</b> 的报障单
          <el-button link type="primary" size="small" @click="reset">清除</el-button>
        </div>
      </div>

      <div class="flex-between" style="margin: 16px 2px 10px">
        <div class="muted" style="font-size: 13px">共 {{ items.length }} 张报障单</div>
        <el-button size="small" :loading="loading" @click="refresh">
          <el-icon><Refresh /></el-icon>&nbsp;刷新
        </el-button>
      </div>

      <div v-if="loading" class="pub-card">
        <el-skeleton :rows="3" animated />
      </div>

      <el-empty
        v-else-if="!items.length"
        :description="activeTail ? `尾号 ${activeTail} 暂无报障记录` : '还没有报障记录'"
      >
        <el-button type="primary" @click="$router.push('/')">去扫码报障</el-button>
      </el-empty>

      <div
        v-for="item in items"
        :key="item.code"
        class="pub-card ticket-item"
        @click="openDetail(item)"
      >
        <div class="flex-between">
          <div class="gap-8">
            <span class="status-dot" :style="{ background: statusMeta(item.status).color }"></span>
            <b style="font-size: 14px">{{ item.device }}</b>
          </div>
          <el-tag :type="statusMeta(item.status).type" size="small" effect="light">
            {{ item.status_text }}
          </el-tag>
        </div>
        <div class="muted" style="font-size: 12.5px; margin-top: 8px">
          📍 {{ item.location }}
        </div>
        <div class="muted" style="font-size: 12.5px; margin-top: 2px" v-if="item.expect_time">
          🕒 期望上门：{{ item.expect_time }}
        </div>
        <div class="flex-between" style="margin-top: 6px">
          <span class="muted mono" style="font-size: 12px">{{ item.code }}</span>
          <span class="muted" style="font-size: 12px">{{ fmtTime(item.created_at) }}</span>
        </div>
        <div v-if="item.status === 'pending_confirm'" class="confirm-tip">
          维修已完成，请确认并签字
          <el-button size="small" type="primary" style="margin-left: auto" @click.stop="openConfirm(item)">
            确认完成
          </el-button>
        </div>
      </div>

      <div class="pub-footer">
        <div>确认维修结果时需要手写签名，签名会随工单一起归档</div>
        <div>如对处理结果有疑问，请先联系运维人员</div>
      </div>
    </div>

    <!-- 详情 -->
    <el-dialog v-model="detailVisible" title="报障详情" width="560px" align-center>
      <ticket-detail
        v-if="current"
        :ticket="current"
        :show-actions="true"
        @confirm="openConfirm(current)"
        @cancel="cancelTicket(current)"
      />
    </el-dialog>

    <!-- 确认 + 评价 + 签名 -->
    <el-dialog v-model="confirmVisible" title="确认维修完成" width="460px" align-center>
      <p class="muted" style="font-size: 13px; margin-top: 0">
        确认后工单将归档，请对本次服务评分并手写签名。
      </p>
      <div style="margin: 8px 0 4px; font-size: 13px">本次服务满意度</div>
      <el-rate
        v-model="confirmForm.rating"
        show-text
        :texts="['很不满意', '不满意', '一般', '满意', '非常满意']"
      />
      <el-input
        v-model="confirmForm.comment"
        type="textarea"
        :rows="2"
        maxlength="200"
        placeholder="补充说明（选填）"
        style="margin-top: 14px"
      />
      <div style="margin: 14px 0 6px; font-size: 13px">
        手写签名 <span style="color: #ef4444">*</span>
      </div>
      <sign-pad ref="signRef" />
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doConfirm">确认完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import { fmtTime, statusMeta } from '../utils'
import TicketDetail from '../components/TicketDetail.vue'
import SignPad from '../components/SignPad.vue'

const TAIL_KEY = 'ops_phone_tail'

const items = ref([])
const loading = ref(false)
const submitting = ref(false)
const detailVisible = ref(false)
const confirmVisible = ref(false)
const current = ref(null)
const tail = ref('')
const activeTail = ref('')
const confirmForm = reactive({ rating: 5, comment: '' })
const signRef = ref(null)

const isLookup = computed(() => !!activeTail.value)

onMounted(() => {
  const saved = (localStorage.getItem(TAIL_KEY) || '').trim()
  if (/^\d{4}$/.test(saved)) {
    tail.value = saved
    doLookup()
  } else {
    loadMine()
  }
})

async function loadMine() {
  loading.value = true
  try {
    const res = await api.myTickets()
    items.value = res.items
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function doLookup() {
  const value = (tail.value || '').trim()
  if (!/^\d{4}$/.test(value)) {
    ElMessage.warning('请输入手机号后四位')
    return
  }
  loading.value = true
  try {
    const res = await api.lookup(value)
    items.value = res.items
    activeTail.value = value
    localStorage.setItem(TAIL_KEY, value)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function refresh() {
  if (isLookup.value) doLookup()
  else loadMine()
}

function reset() {
  localStorage.removeItem(TAIL_KEY)
  activeTail.value = ''
  tail.value = ''
  loadMine()
}

function openDetail(item) {
  current.value = item
  detailVisible.value = true
}

function openConfirm(item) {
  current.value = item
  confirmForm.rating = 5
  confirmForm.comment = ''
  confirmVisible.value = true
  setTimeout(() => signRef.value?.clear(), 50)
}

async function doConfirm() {
  const signature = signRef.value?.toDataURL() || ''
  if (!signature) {
    ElMessage.warning('请先手写签名')
    return
  }
  submitting.value = true
  try {
    await api.confirmTicket(
      current.value.code,
      { rating: confirmForm.rating, comment: confirmForm.comment, signature },
      activeTail.value || ''
    )
    ElMessage.success('已确认，感谢您的评价')
    confirmVisible.value = false
    detailVisible.value = false
    await refresh()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function cancelTicket(item) {
  try {
    await ElMessageBox.confirm('确定撤销这张报障单吗？', '撤销报障', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await api.cancelTicket(item.code)
    ElMessage.success('已撤销')
    detailVisible.value = false
    await refresh()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.ticket-item {
  cursor: pointer;
  transition: all 0.16s;
  margin-top: 12px;
}

.ticket-item:hover {
  box-shadow: var(--shadow);
  transform: translateY(-1px);
}

.confirm-tip {
  margin-top: 12px;
  background: #fff8e8;
  border: 1px solid #f5dfae;
  color: #a1731a;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 12.5px;
  display: flex;
  align-items: center;
}

.tail-note {
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--ink-3);
  background: #f6f9ff;
  border-radius: 8px;
  padding: 6px 10px;
}
</style>
