<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">物资管理</h2>
        <div class="page-sub">维修备件台账 · 按分类自动编号 · 入库 / 领用自动扣减</div>
      </div>
      <div class="gap-8">
        <el-input v-model="keyword" placeholder="搜索名称 / 编号 / 规格" :prefix-icon="Search" clearable style="width: 210px" @keyup.enter="load" @clear="load" />
        <el-select v-model="category" placeholder="全部分类" clearable style="width: 130px" @change="load">
          <el-option v-for="c in categoryList" :key="c.id" :label="`${c.name}（${c.prefix}）`" :value="c.name" />
        </el-select>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <template v-if="isManager">
          <el-button :icon="Upload" @click="openImport">批量导入</el-button>
          <el-button type="primary" :icon="Plus" @click="openEdit()">新增物资</el-button>
        </template>
      </div>
    </div>

    <el-alert
      v-if="lowCount"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 14px; border-radius: 10px"
      :title="`${lowCount} 种物资库存低于预警线，请及时补货`"
    />

    <div class="section-card">
      <div class="muted" style="font-size: 13px; margin-bottom: 10px">
        共 {{ items.length }} 种物资 · 编号按分类前缀自动生成
      </div>
      <el-table class="desktop-table" :data="items" v-loading="loading">
        <el-table-column prop="code" label="编号" width="105">
          <template #default="{ row }"><span class="mono" style="font-size: 12.5px">{{ row.code }}</span></template>
        </el-table-column>
        <el-table-column label="物资" min-width="220">
          <template #default="{ row }">
            <div style="font-weight: 600">{{ row.name }}</div>
            <div class="muted" style="font-size: 12px">{{ row.spec || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="90" />
        <el-table-column label="库存" width="110" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.stock <= row.warn_stock ? '#e6a23c' : '#1f2937', fontWeight: 600 }">
              {{ row.stock }} {{ row.unit }}
            </span>
            <div v-if="row.stock <= row.warn_stock" style="font-size: 11.5px; color: #e6a23c">低于预警</div>
          </template>
        </el-table-column>
        <el-table-column prop="warn_stock" label="预警值" width="80" align="center" />
        <el-table-column prop="location" label="存放位置" width="120" show-overflow-tooltip />
        <el-table-column label="单价" width="90" align="right">
          <template #default="{ row }">¥{{ money(row.unit_price) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openStock(row, 'in')">入库</el-button>
            <el-button link type="primary" @click="openStock(row, 'out')">出库</el-button>
            <el-button link @click="openLogs(row)">流水</el-button>
            <el-button v-if="isManager" link type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
        <template #empty><div class="empty-hint">暂无物资，请新增或批量导入</div></template>
      </el-table>

      <div class="m-card-list" v-loading="loading">
        <div v-for="row in items" :key="row.id" class="m-data-card">
          <div class="m-card-head">
            <span class="mono" style="font-size: 11.5px; color: var(--ink-3)">{{ row.code }}</span>
            <el-tag size="small" effect="plain" type="info">{{ row.category }}</el-tag>
          </div>
          <div class="m-card-title">{{ row.name }}</div>
          <div class="m-card-sub">{{ row.spec || '—' }}</div>
          <div class="m-card-row">
            <span class="label">库存</span>
            <span class="value" :style="{ color: row.stock <= row.warn_stock ? '#e6a23c' : '#1f2937', fontWeight: 600 }">
              {{ row.stock }} {{ row.unit }}
              <span v-if="row.stock <= row.warn_stock" style="font-size: 11px"> · 低于预警</span>
            </span>
          </div>
          <div class="m-card-row"><span class="label">存放位置</span><span class="value">{{ row.location || '—' }}</span></div>
          <div class="m-card-actions">
            <el-button size="small" @click="openStock(row, 'in')">入库</el-button>
            <el-button size="small" @click="openStock(row, 'out')">出库</el-button>
            <el-button size="small" @click="openLogs(row)">流水</el-button>
            <el-button v-if="isManager" size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          </div>
        </div>
        <div v-if="!items.length" class="empty-hint">暂无物资，请新增或批量导入</div>
      </div>
    </div>

    <!-- 新增/编辑物资 -->
    <el-dialog v-model="editVisible" :title="form.id ? '编辑物资' : '新增物资'" width="560px" align-center>
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="物资名称" required>
              <el-input v-model="form.name" placeholder="如 六类网线" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" required>
              <el-select v-model="form.category_id" placeholder="请选择分类" style="width: 100%">
                <el-option v-for="c in categoryList" :key="c.id" :label="`${c.name}（${c.prefix}）`" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="物资编号">
          <el-input :model-value="form.id ? form.code : autoCodeHint" disabled />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="规格型号">
              <el-input v-model="form.spec" placeholder="如 超六类 305米/箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位">
              <el-input v-model="form.unit" placeholder="个" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item :label="form.id ? '当前库存' : '初始库存'">
              <el-input-number v-model="form.stock" :min="0" :precision="1" style="width: 100%" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="库存预警值">
              <el-input-number v-model="form.warn_stock" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单价（元）">
              <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="存放位置">
          <el-input v-model="form.location" placeholder="如 机房A柜" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="saveMaterial">保存</el-button>
      </template>
    </el-dialog>

    <!-- 入库/出库 -->
    <el-dialog v-model="stockVisible" :title="stockKind === 'in' ? '物资入库' : '物资出库'" width="420px" align-center>
      <div v-if="current" class="muted" style="font-size: 13px; margin-bottom: 14px">
        {{ current.name }} · {{ current.spec }} · 当前库存 {{ current.stock }} {{ current.unit }}
      </div>
      <el-form label-position="top">
        <el-form-item :label="stockKind === 'in' ? '入库数量' : '出库数量'" required>
          <el-input-number v-model="stockForm.qty" :min="0.1" :precision="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="stockForm.note" :placeholder="stockKind === 'in' ? '如 采购入库、供应商送货' : '如 日常领用'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stockVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doStock">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入 -->
    <el-dialog v-model="importVisible" title="批量导入物资" width="560px" align-center>
      <el-steps :active="importStep" simple style="margin-bottom: 16px">
        <el-step title="下载模板" />
        <el-step title="填写并上传" />
        <el-step title="导入完成" />
      </el-steps>

      <el-alert type="info" :closable="false" style="margin-bottom: 12px; border-radius: 8px">
        <div style="line-height: 1.9; font-size: 12.5px">
          1. 下载模板，按列填写：名称、分类、规格、单位、初始库存、预警库存、存放位置、单价、备注<br />
          2. 分类必须是系统中已有的分类：{{ categoryList.map((c) => c.name).join('、') || '请先在系统设置中添加' }}<br />
          3. 物资编号会按分类前缀自动生成，无需填写
        </div>
      </el-alert>

      <div class="gap-8" style="margin-bottom: 14px">
        <el-button :icon="Download" @click="downloadTemplate">下载导入模板（CSV）</el-button>
        <span class="muted" style="font-size: 12px">用 Excel 打开填写后另存为 CSV</span>
      </div>

      <input
        ref="fileInput"
        type="file"
        accept=".csv,text/csv"
        style="display: none"
        @change="onFile"
      />
      <el-button :icon="Upload" @click="fileInput?.click()">选择 CSV 文件</el-button>
      <span v-if="importFileName" class="muted" style="font-size: 12.5px; margin-left: 8px">
        {{ importFileName }}
      </span>

      <el-alert
        v-if="importResult"
        :type="importResult.errors.length ? 'warning' : 'success'"
        :closable="false"
        style="margin-top: 14px; border-radius: 8px"
      >
        <div>成功导入 {{ importResult.created }} 条</div>
        <div v-for="(err, i) in importResult.errors" :key="i" style="font-size: 12px; margin-top: 4px">
          第 {{ err.line }} 行：{{ err.message }}
        </div>
      </el-alert>

      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button type="primary" :loading="submitting" :disabled="!importContent" @click="doImport">
          开始导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 流水 -->
    <el-drawer v-model="logsVisible" size="560px" :title="`出入库流水 · ${current?.name || ''}`">
      <el-table :data="logs" v-loading="logsLoading" size="small">
        <el-table-column label="类型" width="70">
          <template #default="{ row }">
            <el-tag :type="row.kind === 'in' ? 'success' : 'warning'" size="small" effect="light">
              {{ row.kind === 'in' ? '入库' : row.kind === 'out' ? '出库' : '调整' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.kind === 'in' ? '#67c23a' : '#e6a23c' }">
              {{ row.kind === 'in' ? '+' : '-' }}{{ row.qty }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="结存" width="80" align="center">
          <template #default="{ row }">{{ row.after_stock }}</template>
        </el-table-column>
        <el-table-column label="关联工单" width="140">
          <template #default="{ row }">
            <span class="mono" style="font-size: 12px">{{ row.ticket_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="经办人" width="80" />
        <el-table-column prop="note" label="备注" show-overflow-tooltip />
        <el-table-column label="时间" width="130">
          <template #default="{ row }"><span class="muted" style="font-size: 12px">{{ fmtTime(row.created_at) }}</span></template>
        </el-table-column>
        <template #empty><div class="empty-hint">暂无流水记录</div></template>
      </el-table>
      <div style="display: flex; justify-content: flex-end; margin-top: 12px">
        <el-pagination
          v-model:current-page="logPage"
          :page-size="20"
          :total="logTotal"
          layout="total, prev, pager, next"
          small
          @current-change="loadLogs"
        />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth } from '../store'
import { fmtTime, hasRole, money } from '../utils'

const items = ref([])
const categories = ref([])
const categoryList = ref([])
const loading = ref(false)
const keyword = ref('')
const category = ref('')
const isManager = computed(() => hasRole(auth.staff, 'admin') || hasRole(auth.staff, 'dispatcher'))
const lowCount = computed(() => items.value.filter((i) => i.stock <= i.warn_stock).length)

const editVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  id: null, code: '', name: '', category_id: null, spec: '', unit: '个',
  stock: 0, warn_stock: 0, location: '', unit_price: 0,
})

const stockVisible = ref(false)
const stockKind = ref('in')
const current = ref(null)
const stockForm = reactive({ qty: 1, note: '' })

const logsVisible = ref(false)
const logs = ref([])
const logsLoading = ref(false)
const logPage = ref(1)
const logTotal = ref(0)

const importVisible = ref(false)
const importStep = ref(0)
const importContent = ref('')
const importFileName = ref('')
const importResult = ref(null)
const fileInput = ref(null)

const autoCodeHint = computed(() => {
  const cat = categoryList.value.find((c) => c.id === form.category_id)
  if (!cat) return '请先选择分类，保存后自动生成编号'
  const nums = items.value
    .filter((i) => i.category_id === cat.id)
    .map((i) => Number((i.code.split('-')[1] || '0')))
    .filter((n) => !Number.isNaN(n))
  const next = (nums.length ? Math.max(...nums) : 0) + 1
  return `${cat.prefix}-${String(next).padStart(3, '0')}`
})

onMounted(async () => {
  await load()
  await loadCategories()
})

async function load() {
  loading.value = true
  try {
    const res = await api.materials({ keyword: keyword.value, category: category.value, page_size: 200 })
    items.value = res.items
    categories.value = res.categories || []
    if (!categoryList.value.length) {
      const c = await api.categories()
      categoryList.value = c.items
    }
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const res = await api.categories()
    categoryList.value = res.items
  } catch (e) {
    /* ignore */
  }
}

function openEdit(row) {
  if (row) {
    Object.assign(form, {
      id: row.id, code: row.code, name: row.name, category_id: row.category_id,
      spec: row.spec, unit: row.unit, stock: row.stock, warn_stock: row.warn_stock,
      location: row.location, unit_price: row.unit_price,
    })
  } else {
    Object.assign(form, {
      id: null, code: '', name: '', category_id: categoryList.value[0]?.id || null,
      spec: '', unit: '个', stock: 0, warn_stock: 0, location: '', unit_price: 0,
    })
  }
  editVisible.value = true
}

async function saveMaterial() {
  if (!form.name || !form.category_id) {
    ElMessage.warning('请填写物资名称并选择分类')
    return
  }
  submitting.value = true
  try {
    if (form.id) {
      await api.updateMaterial(form.id, {
        name: form.name, category_id: form.category_id, spec: form.spec, unit: form.unit,
        warn_stock: form.warn_stock, location: form.location, unit_price: form.unit_price,
      })
    } else {
      const res = await api.createMaterial({
        name: form.name, category_id: form.category_id, spec: form.spec, unit: form.unit,
        stock: form.stock, warn_stock: form.warn_stock, location: form.location,
        unit_price: form.unit_price,
      })
      ElMessage.success(`已新增，编号 ${res.code}`)
    }
    if (form.id) ElMessage.success('保存成功')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

function openStock(row, kind) {
  current.value = row
  stockKind.value = kind
  stockForm.qty = 1
  stockForm.note = ''
  stockVisible.value = true
}

async function doStock() {
  submitting.value = true
  try {
    if (stockKind.value === 'in') {
      await api.inbound(current.value.id, { qty: stockForm.qty, note: stockForm.note })
    } else {
      await api.outbound(current.value.id, { qty: stockForm.qty, note: stockForm.note })
    }
    ElMessage.success(stockKind.value === 'in' ? '入库成功' : '出库成功')
    stockVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function openLogs(row) {
  current.value = row
  logPage.value = 1
  logsVisible.value = true
  await loadLogs()
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const res = await api.stockLogs({ material_id: current.value.id, page: logPage.value, page_size: 20 })
    logs.value = res.items
    logTotal.value = res.total
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    logsLoading.value = false
  }
}

function openImport() {
  importVisible.value = true
  importStep.value = 0
  importContent.value = ''
  importFileName.value = ''
  importResult.value = null
  loadCategories()
}

function downloadTemplate() {
  window.open('/api/staff/materials/template.csv', '_blank')
}

function onFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  importFileName.value = file.name
  const reader = new FileReader()
  reader.onload = () => {
    importContent.value = String(reader.result || '')
    importResult.value = null
    importStep.value = 1
  }
  reader.readAsText(file, 'utf-8')
}

async function doImport() {
  submitting.value = true
  try {
    const res = await api.importMaterials(importContent.value)
    importResult.value = res
    importStep.value = 2
    ElMessage.success(`成功导入 ${res.created} 条`)
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
:deep(.el-step__title) {
  white-space: nowrap;
  font-size: 12.5px;
}
</style>
