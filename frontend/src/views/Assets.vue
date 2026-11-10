<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">设备台账</h2>
        <div class="page-sub">资产位置 · 上架时间 · 网络信息 · 管理账号密码</div>
      </div>
      <div class="gap-8">
        <el-input v-model="keyword" placeholder="搜索名称 / IP / 责任人" :prefix-icon="Search" clearable style="width: 210px" @keyup.enter="reload" @clear="reload" />
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <template v-if="canManage">
          <el-button :icon="Upload" @click="openImport">导入</el-button>
          <el-button type="primary" :icon="Plus" @click="openEdit()">新增设备</el-button>
        </template>
      </div>
    </div>

    <div class="section-card">
      <div class="filter-row">
        <el-select v-model="category" placeholder="全部类型" clearable style="width: 140px" @change="reload">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-select v-model="status" placeholder="全部状态" clearable style="width: 120px" @change="reload">
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="roomId" placeholder="全部房间" clearable filterable style="width: 220px" @change="reload">
          <el-option v-for="r in rooms" :key="r.id" :label="r.location" :value="r.id" />
        </el-select>
        <span class="muted" style="font-size: 13px">共 {{ total }} 台设备</span>
      </div>

      <el-table class="desktop-table" :data="items" v-loading="loading" @row-click="openDetail" style="cursor: pointer">
        <el-table-column prop="code" label="资产编号" width="92">
          <template #default="{ row }"><span class="mono" style="font-size: 12.5px">{{ row.code }}</span></template>
        </el-table-column>
        <el-table-column label="设备" min-width="150">
          <template #default="{ row }">
            <div style="font-weight: 600">{{ row.name }}</div>
            <div class="muted" style="font-size: 12px">{{ row.brand_model || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="类型" width="80" />
        <el-table-column label="位置" min-width="150">
          <template #default="{ row }">
            <div style="font-size: 12.5px">{{ row.location || '—' }}</div>
            <div class="muted" style="font-size: 12px">{{ row.rack_position || '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="网络 / 管理地址" min-width="175">
          <template #default="{ row }">
            <div class="mono ellipsis" style="font-size: 12px" :title="row.mgmt_address">{{ row.mgmt_address || '—' }}</div>
            <div class="muted ellipsis" style="font-size: 11.5px">{{ row.network || '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="管理账号" width="100">
          <template #default="{ row }">
            <div class="ellipsis" style="font-size: 12.5px">{{ row.mgmt_user || '—' }}</div>
            <div class="muted" style="font-size: 11.5px; white-space: nowrap">{{ row.password_set ? '密码已设置' : '未设密码' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="install_date" label="上架时间" width="108">
          <template #default="{ row }"><span class="muted" style="font-size: 12.5px; white-space: nowrap">{{ row.install_date || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="72">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="light">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="112" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openDetail(row)">详情</el-button>
            <el-button v-if="canManage" link type="primary" @click.stop="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
        <template #empty><div class="empty-hint">暂无设备，点击「新增设备」或「导入」</div></template>
      </el-table>

      <div class="m-card-list" v-loading="loading">
        <div v-for="row in items" :key="row.id" class="m-data-card" @click="openDetail(row)">
          <div class="m-card-head">
            <span class="mono" style="font-size: 11.5px; color: var(--ink-3)">{{ row.code }}</span>
            <el-tag size="small" :type="statusType(row.status)" effect="light">{{ row.status }}</el-tag>
          </div>
          <div class="m-card-title">{{ row.name }}</div>
          <div class="m-card-sub">{{ row.brand_model || '—' }} · {{ row.category }}</div>
          <div class="m-card-row"><span class="label">位置</span><span class="value">{{ row.location || '—' }}</span></div>
          <div class="m-card-row"><span class="label">机柜</span><span class="value">{{ row.rack_position || '—' }}</span></div>
          <div class="m-card-row"><span class="label">管理地址</span><span class="value mono">{{ row.mgmt_address || '—' }}</span></div>
          <div class="m-card-row"><span class="label">管理账号</span><span class="value">{{ row.mgmt_user || '—' }}</span></div>
          <div class="m-card-actions">
            <el-button size="small" type="primary" @click.stop="openDetail(row)">详情</el-button>
            <el-button v-if="canManage" size="small" @click.stop="openEdit(row)">编辑</el-button>
          </div>
        </div>
        <div v-if="!items.length" class="empty-hint">暂无设备</div>
      </div>

      <div style="display: flex; justify-content: flex-end; margin-top: 14px">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="total, prev, pager, next" background @current-change="load" />
      </div>
    </div>

    <!-- 详情 -->
    <el-drawer v-model="detailVisible" size="640px" :with-header="false" destroy-on-close>
      <div v-if="detail" style="padding: 4px 4px 10px">
        <div class="detail-head">
          <div>
            <div style="font-size: 19px; font-weight: 700">{{ detail.name }}</div>
            <div class="detail-code">{{ detail.code }} · {{ detail.category }}</div>
          </div>
          <el-tag :type="statusType(detail.status)" effect="light" size="large">{{ detail.status }}</el-tag>
        </div>

        <div class="sub-label">基本信息</div>
        <div class="info-grid">
          <div class="info-item"><div class="k">品牌型号</div><div class="v">{{ detail.brand_model || '—' }}</div></div>
          <div class="info-item"><div class="k">序列号</div><div class="v mono">{{ detail.serial_no || '—' }}</div></div>
          <div class="info-item"><div class="k">所在房间</div><div class="v">{{ detail.location || '—' }}</div></div>
          <div class="info-item"><div class="k">位置 / 机柜</div><div class="v">{{ detail.rack_position || '—' }}</div></div>
          <div class="info-item"><div class="k">上架时间</div><div class="v">{{ detail.install_date || '—' }}</div></div>
          <div class="info-item"><div class="k">保修到期</div><div class="v">{{ detail.warranty_until || '—' }}</div></div>
        </div>

        <div class="sub-label">网络与管理</div>
        <div class="info-grid">
          <div class="info-item full"><div class="k">网络信息</div><div class="v">{{ detail.network || '—' }}</div></div>
          <div class="info-item full"><div class="k">管理地址</div><div class="v mono">{{ detail.mgmt_address || '—' }}</div></div>
          <div class="info-item"><div class="k">管理账号</div><div class="v mono">{{ detail.mgmt_user || '—' }}</div></div>
          <div class="info-item"><div class="k">管理端口</div><div class="v">{{ detail.mgmt_port || '—' }}</div></div>
          <div class="info-item full">
            <div class="k">管理密码</div>
            <div class="v" style="display: flex; align-items: center; gap: 8px">
              <span class="mono">{{ revealedPassword ?? (detail.password_set ? '••••••••' : '未设置') }}</span>
              <template v-if="detail.password_set">
                <el-button v-if="isAdmin && revealedPassword === null" link type="primary" size="small" :loading="revealing" @click="revealPassword">
                  显示密码
                </el-button>
                <el-button v-if="revealedPassword !== null" link size="small" @click="copy(revealedPassword)">复制</el-button>
                <el-button v-if="revealedPassword !== null" link size="small" @click="revealedPassword = null">隐藏</el-button>
              </template>
              <span v-if="detail.password_set && !isAdmin" class="muted" style="font-size: 11.5px">仅管理员可查看明文</span>
            </div>
          </div>
        </div>

        <div class="sub-label">其他</div>
        <div class="info-grid">
          <div class="info-item"><div class="k">责任人</div><div class="v">{{ detail.owner || '—' }}</div></div>
          <div class="info-item"><div class="k">供应商</div><div class="v">{{ detail.vendor || '—' }}</div></div>
          <div class="info-item full"><div class="k">备注</div><div class="v">{{ detail.note || '—' }}</div></div>
        </div>

        <div style="margin-top: 20px; display: flex; gap: 8px">
          <el-button v-if="canManage" type="primary" @click="openEdit(detail)">编辑</el-button>
          <el-button v-if="canManage" type="danger" plain @click="remove(detail)">删除</el-button>
        </div>
      </div>
      <el-skeleton v-else :rows="8" animated />
    </el-drawer>

    <!-- 新增/编辑 -->
    <el-dialog v-model="editVisible" :title="form.id ? '编辑设备' : '新增设备'" width="760px" align-center>
      <el-form label-position="top">
        <div class="form-section-title">基本信息</div>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="设备名称" required><el-input v-model="form.name" placeholder="如 核心交换机" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="设备类型">
              <el-select v-model="form.category" style="width: 100%">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="品牌型号"><el-input v-model="form.brand_model" placeholder="如 华为 S5735" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="序列号"><el-input v-model="form.serial_no" placeholder="SN 序列号" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="资产编号">
              <el-input :model-value="form.id ? form.code : '保存后自动生成 ZC-编号'" disabled />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-section-title">位置与上架</div>
        <el-row :gutter="12">
          <el-col :span="10">
            <el-form-item label="所在房间">
              <el-select v-model="form.room_id" filterable clearable placeholder="选择房间" style="width: 100%">
                <el-option v-for="r in rooms" :key="r.id" :label="r.location" :value="r.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="位置 / 机柜"><el-input v-model="form.rack_position" placeholder="如 A01 机柜 U12" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="上架时间">
              <el-date-picker v-model="form.install_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <div class="form-section-title">网络与管理</div>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="网络信息"><el-input v-model="form.network" placeholder="如 VLAN 10 / 192.168.10.1" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="管理地址"><el-input v-model="form.mgmt_address" placeholder="如 https://192.168.10.1" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="管理账号"><el-input v-model="form.mgmt_user" placeholder="admin" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="form.id ? '管理密码（留空不修改）' : '管理密码'">
              <el-input v-model="form.mgmt_password" type="password" show-password :placeholder="form.id && form.password_set ? '已设置，留空不修改' : '请输入密码'" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="管理端口"><el-input v-model="form.mgmt_port" placeholder="443" /></el-form-item>
          </el-col>
        </el-row>

        <div class="form-section-title">其他</div>
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="责任人"><el-input v-model="form.owner" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="供应商"><el-input v-model="form.vendor" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="保修到期">
              <el-date-picker v-model="form.warranty_until" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入 -->
    <el-dialog v-model="importVisible" title="批量导入设备" width="560px" align-center>
      <el-alert type="info" :closable="false" style="margin-bottom: 12px; border-radius: 8px">
        <div style="line-height: 1.9; font-size: 12.5px">
          1. 下载模板（.xlsx），按列填写后保存<br />
          2. 支持 .xlsx 与 .csv；资产编号可留空自动生成<br />
          3. 管理密码导入后加密保存，仅管理员可查看
        </div>
      </el-alert>
      <div class="gap-8" style="margin-bottom: 14px">
        <el-button :icon="Download" @click="downloadTemplate">下载导入模板（Excel）</el-button>
        <span class="muted" style="font-size: 12px">也可使用 CSV 文件</span>
      </div>
      <input ref="fileInput" type="file" accept=".xlsx,.xlsm,.csv" style="display: none" @change="onFile" />
      <el-button :icon="Upload" @click="fileInput?.click()">选择文件</el-button>
      <span v-if="importFileName" class="muted" style="font-size: 12.5px; margin-left: 8px">{{ importFileName }}</span>

      <el-alert v-if="importResult" :type="importResult.errors.length ? 'warning' : 'success'" :closable="false" style="margin-top: 14px; border-radius: 8px">
        <div>成功导入 {{ importResult.created }} 条</div>
        <div v-for="(err, i) in importResult.errors" :key="i" style="font-size: 12px; margin-top: 4px">
          第 {{ err.line }} 行：{{ err.message }}
        </div>
      </el-alert>

      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button type="primary" :loading="saving" :disabled="!importContent" @click="doImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth } from '../store'
import { can } from '../utils'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const saving = ref(false)
const keyword = ref('')
const category = ref('')
const status = ref('')
const roomId = ref(null)
const categories = ref([])
const statuses = ref([])
const rooms = ref([])

const detailVisible = ref(false)
const detail = ref(null)
const revealedPassword = ref(null)
const revealing = ref(false)

const editVisible = ref(false)
const form = reactive({
  id: null, code: '', name: '', category: '网络设备', brand_model: '', serial_no: '',
  room_id: null, rack_position: '', install_date: '', status: '在用', network: '',
  mgmt_address: '', mgmt_user: '', mgmt_password: '', mgmt_port: '', owner: '',
  vendor: '', warranty_until: '', note: '', password_set: false,
})

const importVisible = ref(false)
const importFileName = ref('')
const importContent = ref('')
const importResult = ref(null)
const fileInput = ref(null)

const isAdmin = computed(() => can(auth.staff, 'asset.password'))
const canManage = computed(() => can(auth.staff, 'asset.manage'))

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})

async function loadMeta() {
  try {
    const meta = await api.assetMeta()
    categories.value = meta.categories
    statuses.value = meta.statuses
    rooms.value = meta.rooms
  } catch (e) {
    /* ignore */
  }
}

async function load() {
  loading.value = true
  try {
    const res = await api.assets({
      keyword: keyword.value, category: category.value, status: status.value,
      room_id: roomId.value || 0, page: page.value, page_size: pageSize,
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
  load()
}

function statusType(value) {
  return { 在用: 'success', 备用: 'info', 维修: 'warning', 报废: 'danger' }[value] || 'info'
}

function openDetail(row) {
  detail.value = row
  revealedPassword.value = null
  detailVisible.value = true
}

async function revealPassword() {
  revealing.value = true
  try {
    const res = await api.revealAssetPassword(detail.value.id)
    revealedPassword.value = res.password || '（空）'
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    revealing.value = false
  }
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch (e) {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

function openEdit(row) {
  if (row) {
    Object.assign(form, {
      id: row.id, code: row.code, name: row.name, category: row.category,
      brand_model: row.brand_model, serial_no: row.serial_no, room_id: row.room_id,
      rack_position: row.rack_position, install_date: row.install_date,
      status: row.status, network: row.network, mgmt_address: row.mgmt_address,
      mgmt_user: row.mgmt_user, mgmt_password: '', mgmt_port: row.mgmt_port,
      owner: row.owner, vendor: row.vendor, warranty_until: row.warranty_until,
      note: row.note, password_set: row.password_set,
    })
  } else {
    Object.assign(form, {
      id: null, code: '', name: '', category: '网络设备', brand_model: '', serial_no: '',
      room_id: null, rack_position: '', install_date: '', status: '在用', network: '',
      mgmt_address: '', mgmt_user: '', mgmt_password: '', mgmt_port: '', owner: '',
      vendor: '', warranty_until: '', note: '', password_set: false,
    })
  }
  detailVisible.value = false
  editVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写设备名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name, category: form.category, brand_model: form.brand_model,
      serial_no: form.serial_no, room_id: form.room_id || null,
      rack_position: form.rack_position, install_date: form.install_date,
      status: form.status, network: form.network, mgmt_address: form.mgmt_address,
      mgmt_user: form.mgmt_user, mgmt_port: form.mgmt_port, owner: form.owner,
      vendor: form.vendor, warranty_until: form.warranty_until, note: form.note,
    }
    if (form.mgmt_password) payload.mgmt_password = form.mgmt_password
    if (form.id) {
      await api.updateAsset(form.id, payload)
      ElMessage.success('已保存')
    } else {
      const res = await api.createAsset(payload)
      ElMessage.success(`已新增，资产编号 ${res.code}`)
    }
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除设备「${row.name}」？`, '删除设备', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await api.deleteAsset(row.id)
    ElMessage.success('已删除')
    detailVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function downloadTemplate() {
  window.open('/api/staff/assets/template.xlsx', '_blank')
}

function openImport() {
  importVisible.value = true
  importFileName.value = ''
  importContent.value = ''
  importResult.value = null
}

function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    importFileName.value = file.name
    importContent.value = String(reader.result || '')
    importResult.value = null
  }
  reader.readAsDataURL(file)
}

async function doImport() {
  saving.value = true
  try {
    const res = await api.importAssets({
      filename: importFileName.value,
      content_base64: importContent.value,
    })
    importResult.value = res
    ElMessage.success(`成功导入 ${res.created} 条`)
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.filter-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.sub-label {
  font-size: 12px;
  color: var(--ink-3);
  margin: 18px 0 8px;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 18px;
}
.info-item .k {
  color: var(--ink-3);
  font-size: 12px;
}
.info-item .v {
  font-size: 13.5px;
  font-weight: 500;
  word-break: break-all;
}
.info-item.full {
  grid-column: span 2;
}
.form-section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--blue, #2f6feb);
  border-left: 3px solid #2f6feb;
  padding-left: 8px;
  margin: 4px 0 12px;
}
</style>
