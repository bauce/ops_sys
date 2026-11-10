<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">房间与二维码</h2>
        <div class="page-sub">一房一码，贴在房间门旁，扫码即可报障</div>
      </div>
      <div class="gap-8">
        <el-input v-model="keyword" placeholder="搜索楼栋 / 房间号 / 名称" :prefix-icon="Search" clearable style="width: 240px" @keyup.enter="load" @clear="load" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <el-button v-if="isAdmin" type="primary" :icon="Plus" @click="openEdit()">新增房间</el-button>
      </div>
    </div>

    <el-alert
      v-if="!baseUrl"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 14px; border-radius: 10px"
      title="二维码当前使用「浏览器访问地址」自动生成。若部署在内网服务器，请先到系统设置填写固定访问地址，否则打印出的二维码可能无法在手机上打开。"
    >
      <template #default>
        <el-button link type="primary" @click="$router.push('/admin/settings')">去设置</el-button>
      </template>
    </el-alert>

    <div class="section-card">
      <div class="flex-between" style="margin-bottom: 12px">
        <div class="muted" style="font-size: 13px">
          共 {{ rooms.length }} 个房间<span v-if="selected.length"> · 已选 {{ selected.length }} 个</span>
        </div>
        <div class="gap-8">
          <el-button :disabled="!selected.length" :icon="Printer" @click="printSelected">打印选中标签</el-button>
          <el-button :icon="Printer" @click="printAll">打印全部标签</el-button>
        </div>
      </div>

      <el-table class="desktop-table" :data="rooms" v-loading="loading" @selection-change="(rows) => (selected = rows)">
        <el-table-column type="selection" width="46" />
        <el-table-column label="房间" min-width="200">
          <template #default="{ row }">
            <div style="font-weight: 600">{{ row.building }}{{ row.floor }}层 {{ row.room_no }}室</div>
            <div class="muted" style="font-size: 12px">{{ row.name || '—' }}<span v-if="row.note"> · {{ row.note }}</span></div>
          </template>
        </el-table-column>
        <el-table-column label="重要等级" width="96" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="light"
              :type="row.importance === '核心' ? 'danger' : row.importance === '重要' ? 'warning' : 'info'"
            >{{ row.importance || '普通' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="二维码" width="110" align="center">
          <template #default="{ row }">
            <el-image
              :src="`/api/staff/rooms/${row.id}/qr.png`"
              style="width: 54px; height: 54px; border-radius: 6px; border: 1px solid var(--line); cursor: zoom-in"
              fit="contain"
              @click="preview(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="报障情况" width="130" align="center">
          <template #default="{ row }">
            <div>{{ row.ticket_count }} 单</div>
            <div v-if="row.open_count" style="font-size: 12px; color: #e6a23c">未结 {{ row.open_count }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="preview(row)">二维码</el-button>
            <el-button link type="primary" @click="printOne(row)">打印</el-button>
            <el-dropdown trigger="click" style="margin-left: 8px">
              <el-button link type="primary">更多</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="copyLink(row)">复制报障链接</el-dropdown-item>
                  <el-dropdown-item v-if="isAdmin" @click="openEdit(row)">编辑房间</el-dropdown-item>
                  <el-dropdown-item v-if="isAdmin" @click="regen(row)">重新生成二维码（旧码作废）</el-dropdown-item>
                  <el-dropdown-item v-if="isAdmin" divided @click="removeRoom(row)">删除房间</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
        <template #empty><div class="empty-hint">暂无房间，点击右上角「新增房间」</div></template>
      </el-table>

      <div class="m-card-list" v-loading="loading">
        <div v-for="row in rooms" :key="row.id" class="m-data-card">
          <div class="m-card-flex">
            <div>
              <div class="m-card-head">
                <span class="m-card-title">{{ row.building }}{{ row.floor }}层 {{ row.room_no }}室</span>
                <el-tag
                  size="small"
                  effect="light"
                  :type="row.importance === '核心' ? 'danger' : row.importance === '重要' ? 'warning' : 'info'"
                >{{ row.importance || '普通' }}</el-tag>
              </div>
              <div class="m-card-sub">{{ row.name || '—' }}<span v-if="row.note"> · {{ row.note }}</span></div>
              <div class="m-card-row"><span class="label">报障</span><span class="value">{{ row.ticket_count }} 单<template v-if="row.open_count"> · 未结 {{ row.open_count }}</template></span></div>
            </div>
            <el-image
              :src="`/api/staff/rooms/${row.id}/qr.png`"
              class="m-card-qr"
              fit="contain"
              @click="preview(row)"
            />
          </div>
          <div class="m-card-actions">
            <el-button size="small" @click="preview(row)">二维码</el-button>
            <el-button size="small" @click="printOne(row)">打印</el-button>
            <el-button size="small" @click="copyLink(row)">复制链接</el-button>
            <el-button v-if="isAdmin" size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          </div>
        </div>
        <div v-if="!rooms.length" class="empty-hint">暂无房间</div>
      </div>
    </div>

    <!-- 二维码预览 -->
    <el-dialog v-model="previewVisible" title="房间报障二维码" width="400px" align-center>
      <div v-if="current" style="text-align: center">
        <div style="font-size: 16px; font-weight: 700">
          {{ current.building }}{{ current.floor }}层 {{ current.room_no }}室
        </div>
        <div class="muted" style="font-size: 12.5px; margin-bottom: 14px">{{ current.name }}</div>
        <img :src="`/api/staff/rooms/${current.id}/qr.png`" style="width: 220px; height: 220px" />
        <div class="note-box mono" style="margin-top: 14px; font-size: 11.5px; word-break: break-all">
          {{ qrLink(current) }}
        </div>
        <div class="muted" style="font-size: 12px; margin-top: 8px">建议打印后贴于门旁或设备附近</div>
      </div>
      <template #footer>
        <el-button @click="copyLink(current)">复制链接</el-button>
        <el-button type="primary" @click="printOne(current)">打印该标签</el-button>
      </template>
    </el-dialog>

    <!-- 新增 / 编辑房间 -->
    <el-dialog v-model="editVisible" :title="form.id ? '编辑房间' : '新增房间'" width="440px" align-center>
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="楼栋" required>
              <el-input v-model="form.building" placeholder="如 1号楼" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="楼层" required>
              <el-input v-model="form.floor" placeholder="如 3" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="房间号" required>
              <el-input v-model="form.room_no" placeholder="如 305" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="房间名称">
              <el-input v-model="form.name" placeholder="如 会议室B" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="重要等级">
          <el-radio-group v-model="form.importance">
            <el-radio-button label="普通" />
            <el-radio-button label="重要" />
            <el-radio-button label="核心" />
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" placeholder="如 投影、视频会议设备" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Printer, Refresh, Search } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth } from '../store'
import { can } from '../utils'

const rooms = ref([])
const loading = ref(false)
const keyword = ref('')
const selected = ref([])
const baseUrl = ref('')
const previewVisible = ref(false)
const current = ref(null)
const editVisible = ref(false)
const submitting = ref(false)
const form = reactive({ id: null, building: '', floor: '', room_no: '', name: '', note: '', importance: '普通' })

const isAdmin = computed(() => can(auth.staff, 'room.manage'))

onMounted(async () => {
  await load()
  try {
    const s = await api.settings()
    baseUrl.value = s.public_base_url
  } catch (e) {
    /* ignore */
  }
})

async function load() {
  loading.value = true
  try {
    const res = await api.rooms({ keyword: keyword.value })
    rooms.value = res.items
    selected.value = []
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function qrLink(row) {
  const base = baseUrl.value || location.origin
  return `${base}/r/${row.qr_code}`
}

function preview(row) {
  current.value = row
  previewVisible.value = true
}

async function copyLink(row) {
  const link = qrLink(row)
  try {
    await navigator.clipboard.writeText(link)
    ElMessage.success('链接已复制：' + link)
  } catch (e) {
    ElMessageBox.alert(link, '复制失败，请手动复制')
  }
}

function openEdit(row) {
  form.id = row?.id || null
  form.building = row?.building || ''
  form.floor = row?.floor || ''
  form.room_no = row?.room_no || ''
  form.name = row?.name || ''
  form.note = row?.note || ''
  form.importance = row?.importance || '普通'
  editVisible.value = true
}

async function save() {
  if (!form.building || !form.floor || !form.room_no) {
    ElMessage.warning('请填写楼栋、楼层和房间号')
    return
  }
  submitting.value = true
  try {
    const payload = {
      building: form.building, floor: form.floor, room_no: form.room_no,
      name: form.name, note: form.note, importance: form.importance, active: 1,
    }
    if (form.id) await api.updateRoom(form.id, payload)
    else await api.createRoom(payload)
    ElMessage.success('保存成功')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function regen(row) {
  try {
    await ElMessageBox.confirm(
      '重新生成后，已打印的旧二维码将失效，需要重新打印。确定继续？',
      '重新生成二维码',
      { type: 'warning' }
    )
  } catch (e) {
    return
  }
  try {
    await api.regenQr(row.id)
    ElMessage.success('已重新生成，请重新打印标签')
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function removeRoom(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.building}${row.floor}层${row.room_no}室」？已报障记录会保留。`, '删除房间', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await api.deleteRoom(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function printSelected() {
  const ids = selected.value.map((r) => r.id).join(',')
  window.open(`/print/rooms?ids=${ids}`, '_blank')
}

function printAll() {
  window.open('/print/rooms', '_blank')
}

function printOne(row) {
  window.open(`/print/rooms?ids=${row.id}`, '_blank')
}
</script>
