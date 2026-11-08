<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">系统设置</h2>
        <div class="page-sub">报障字典、物资分类、二维码地址与账号管理</div>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- 故障类型 / 常用设备 -->
      <el-tab-pane label="故障类型与设备" name="dicts">
        <div class="two-col" style="align-items: start">
          <div class="section-card">
            <div class="card-title">
              <span>故障类型</span>
              <span class="muted" style="font-size: 12px">报障时供用户选择</span>
            </div>
            <div class="gap-8" style="margin-bottom: 12px">
              <el-input v-model="newFault" placeholder="新增故障类型" maxlength="30" @keyup.enter="addDict('fault_types')" />
              <el-button type="primary" @click="addDict('fault_types')">添加</el-button>
            </div>
            <el-table :data="faultTypes" size="small">
              <el-table-column prop="name" label="名称" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-switch :model-value="!!row.active" @change="(v) => toggleDict('fault_types', row, v)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" align="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeDict('fault_types', row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="section-card">
            <div class="card-title">
              <span>常用设备</span>
              <span class="muted" style="font-size: 12px">报障页快捷选择</span>
            </div>
            <div class="gap-8" style="margin-bottom: 12px">
              <el-input v-model="newDevice" placeholder="新增设备名称" maxlength="30" @keyup.enter="addDict('devices')" />
              <el-button type="primary" @click="addDict('devices')">添加</el-button>
            </div>
            <el-table :data="devices" size="small" max-height="420">
              <el-table-column prop="name" label="名称" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-switch :model-value="!!row.active" @change="(v) => toggleDict('devices', row, v)" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" align="right">
                <template #default="{ row }">
                  <el-button link type="danger" @click="removeDict('devices', row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <!-- 物资分类 -->
      <el-tab-pane label="物资分类" name="categories">
        <div class="section-card">
          <div class="card-title">
            <span>物资分类与编号前缀</span>
            <el-button type="primary" size="small" :icon="Plus" @click="openCategory()">新增分类</el-button>
          </div>
          <p class="muted" style="font-size: 12.5px; margin-top: -6px">
            新增物资时按分类前缀自动生成编号，例如「线材」前缀为 XC，则编号为 XC-001、XC-002……
          </p>
          <el-table :data="categoryList" size="default">
            <el-table-column prop="name" label="分类名称" width="180" />
            <el-table-column label="编号前缀" width="140">
              <template #default="{ row }"><span class="mono">{{ row.prefix }}-001</span></template>
            </el-table-column>
            <el-table-column prop="material_count" label="物资数量" width="110" align="center" />
            <el-table-column label="操作" align="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openCategory(row)">编辑</el-button>
                <el-button link type="danger" :disabled="row.material_count > 0" @click="removeCategory(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty><div class="empty-hint">暂无分类</div></template>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 二维码地址 -->
      <el-tab-pane v-if="isAdmin" label="二维码地址" name="basic">
        <div class="section-card">
          <div class="card-title">二维码访问地址</div>
          <p class="muted" style="font-size: 13px; margin-top: -6px">
            手机扫码后打开的地址。留空则自动使用本机局域网 IP 生成。
            部署到内网服务器时填写手机可访问的固定地址，例如
            <code>http://192.168.1.50:8008</code>。修改后需重新打印二维码标签。
          </p>
          <div class="gap-8" style="max-width: 640px; margin-top: 12px">
            <el-input v-model="baseUrl" placeholder="如 http://192.168.1.50:8008" clearable />
            <el-button type="primary" :loading="saving" @click="saveBase">保存</el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 邮件配置 -->
      <el-tab-pane v-if="isAdmin" label="邮件通知" name="email">
        <div class="section-card">
          <div class="card-title">
            <span>SMTP 邮件配置</span>
            <el-switch v-model="mail.enabled" active-text="启用派单邮件提醒" />
          </div>
          <p class="muted" style="font-size: 13px; margin-top: -6px">
            配置后，受理员派单、管理员改派、工程师转派时会自动给处理人发送邮件提醒。
            常用邮箱服务：QQ 邮箱 smtp.qq.com:587（STARTTLS）或 465（SSL），企业邮箱请向信息中心确认参数。
          </p>
          <el-form label-position="top" style="max-width: 720px; margin-top: 12px">
            <el-row :gutter="12">
              <el-col :span="14">
                <el-form-item label="SMTP 服务器">
                  <el-input v-model="mail.smtp_host" placeholder="smtp.example.com" />
                </el-form-item>
              </el-col>
              <el-col :span="10">
                <el-form-item label="端口">
                  <el-input v-model="mail.smtp_port" placeholder="587" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="加密方式">
                  <el-select v-model="mail.smtp_secure" style="width: 100%">
                    <el-option label="STARTTLS（常用，587）" value="starttls" />
                    <el-option label="SSL（465）" value="ssl" />
                    <el-option label="不加密（内网 25）" value="none" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="SMTP 账号">
                  <el-input v-model="mail.smtp_user" placeholder="登录邮箱账号" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="SMTP 密码 / 授权码">
              <el-input
                v-model="mail.smtp_password"
                type="password"
                show-password
                :placeholder="mail.password_set ? '已设置，留空表示不修改' : '请输入邮箱授权码'"
              />
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="发件人邮箱">
                  <el-input v-model="mail.mail_from" placeholder="留空则使用 SMTP 账号" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="发件人名称">
                  <el-input v-model="mail.mail_from_name" placeholder="信息化运维系统" />
                </el-form-item>
              </el-col>
            </el-row>
            <div class="gap-8">
              <el-button type="primary" :loading="saving" @click="saveMail">保存配置</el-button>
              <el-input v-model="testTo" placeholder="接收测试邮件的邮箱" style="width: 260px" />
              <el-button :loading="testing" @click="sendTest">发送测试邮件</el-button>
            </div>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 账号 -->
      <el-tab-pane label="运维账号" name="accounts">
        <div class="section-card">
          <div class="card-title">
            <span>{{ isAdmin ? '运维账号' : '运维工程师' }}</span>
            <el-button type="primary" size="small" :icon="Plus" @click="openCreate">
              {{ isAdmin ? '新增账号' : '新增工程师' }}
            </el-button>
          </div>
          <el-table :data="users" v-loading="loading">
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column prop="username" label="登录名" width="140">
              <template #default="{ row }"><span class="mono" style="font-size: 12.5px">{{ row.username }}</span></template>
            </el-table-column>
            <el-table-column label="角色" width="190">
              <template #default="{ row }">
                <el-tag
                  v-for="r in (row.roles || [row.role])"
                  :key="r"
                  size="small"
                  style="margin-right: 4px"
                  :type="r === 'admin' ? 'danger' : r === 'dispatcher' ? 'warning' : 'primary'"
                  effect="light"
                >
                  {{ roleName(r) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="phone" label="电话" width="130" />
            <el-table-column prop="email" label="邮箱" min-width="180">
              <template #default="{ row }">
                <span :class="{ muted: !row.email }">{{ row.email || '未填写' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-switch
                  :model-value="!!row.active"
                  :disabled="row.username === 'admin'"
                  @change="(v) => toggleActive(row, v)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" align="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEditUser(row)">编辑</el-button>
                <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="section-card">
          <div class="card-title">角色说明</div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统管理员">全部权限：工单、电话代录、转派、物资、分类与字典、房间二维码、邮件配置、账号管理</el-descriptions-item>
            <el-descriptions-item label="报障受理员">受理派单、电话代录、改派与大屏、物资与分类、字典维护、运维工程师账号管理</el-descriptions-item>
            <el-descriptions-item label="运维工程师">查看指派给自己的工单、上门处理、登记领用物资、发起转派（需对方接收）</el-descriptions-item>
            <el-descriptions-item label="普通用户（报障人）">无需账号，扫房间二维码报障，凭手机号后四位查询与签字确认</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑分类 -->
    <el-dialog v-model="categoryVisible" :title="categoryForm.id ? '编辑分类' : '新增分类'" width="400px" align-center>
      <el-form label-position="top">
        <el-form-item label="分类名称" required>
          <el-input v-model="categoryForm.name" placeholder="如 线材" />
        </el-form-item>
        <el-form-item label="编号前缀" required>
          <el-input v-model="categoryForm.prefix" placeholder="如 XC（1-4 位字母）" maxlength="4" />
        </el-form-item>
        <div class="muted" style="font-size: 12px">
          编号示例：{{ (categoryForm.prefix || 'XC').toUpperCase() }}-001
        </div>
      </el-form>
      <template #footer>
        <el-button @click="categoryVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="saveCategory">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增账号 -->
    <el-dialog v-model="createVisible" title="新增运维账号" width="440px" align-center>
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="姓名" required><el-input v-model="createForm.name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="登录名" required><el-input v-model="createForm.username" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="角色（可多选，如同时是受理员与工程师）" required>
          <el-checkbox-group v-model="createForm.roles" :disabled="!isAdmin">
            <el-checkbox label="engineer">运维工程师</el-checkbox>
            <el-checkbox label="dispatcher">报障受理员</el-checkbox>
            <el-checkbox label="admin">系统管理员</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="电话"><el-input v-model="createForm.phone" /></el-form-item>
        <el-form-item label="邮箱（用于接收派单提醒）">
          <el-input v-model="createForm.email" placeholder="name@company.com" />
        </el-form-item>
        <el-form-item label="初始密码" required><el-input v-model="createForm.password" placeholder="至少 6 位" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑账号 -->
    <el-dialog v-model="editUserVisible" title="编辑账号" width="440px" align-center>
      <el-form label-position="top">
        <el-form-item label="姓名"><el-input v-model="editUserForm.name" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="电话"><el-input v-model="editUserForm.phone" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色">
              <el-checkbox-group v-model="editUserForm.roles" :disabled="!isAdmin">
                <el-checkbox label="engineer">运维工程师</el-checkbox>
                <el-checkbox label="dispatcher">受理员</el-checkbox>
                <el-checkbox label="admin">管理员</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="邮箱（用于接收派单提醒）">
          <el-input v-model="editUserForm.email" placeholder="name@company.com" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editUserVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="resetVisible" title="重置密码" width="400px" align-center>
      <div class="muted" style="font-size: 13px; margin-bottom: 12px">{{ resetUser?.name }}（{{ resetUser?.username }}）</div>
      <el-input v-model="resetPassword" placeholder="输入新密码，至少 6 位" show-password />
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="doReset">确定重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth } from '../store'
import { hasRole } from '../utils'

const activeTab = ref('dicts')
const isAdmin = computed(() => hasRole(auth.staff, 'admin'))

const faultTypes = ref([])
const devices = ref([])
const newFault = ref('')
const newDevice = ref('')
const categoryList = ref([])
const categoryVisible = ref(false)
const categoryForm = reactive({ id: null, name: '', prefix: '' })

const baseUrl = ref('')
const saving = ref(false)
const users = ref([])
const loading = ref(false)
const createVisible = ref(false)
const resetVisible = ref(false)
const editUserVisible = ref(false)
const editUserForm = reactive({ id: null, name: '', phone: '', email: '', roles: [] })
const mail = reactive({
  smtp_host: '', smtp_port: '587', smtp_secure: 'starttls', smtp_user: '',
  smtp_password: '', mail_from: '', mail_from_name: '信息化运维系统',
  enabled: false, password_set: false,
})
const testTo = ref('')
const testing = ref(false)
const resetUser = ref(null)
const resetPassword = ref('')
const submitting = ref(false)
const createForm = reactive({ name: '', username: '', roles: ['engineer'], phone: '', email: '', password: '' })

onMounted(async () => {
  await Promise.all([loadDicts(), loadCategories()])
  await loadUsers()
  if (isAdmin.value) await Promise.all([loadSettings(), loadEmail()])
})

async function loadDicts() {
  try {
    const [f, d] = await Promise.all([api.dicts('fault_types'), api.dicts('devices')])
    faultTypes.value = f.items
    devices.value = d.items
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function addDict(kind) {
  const name = (kind === 'fault_types' ? newFault.value : newDevice.value).trim()
  if (!name) {
    ElMessage.warning('请输入名称')
    return
  }
  try {
    await api.createDict(kind, { name })
    if (kind === 'fault_types') newFault.value = ''
    else newDevice.value = ''
    await loadDicts()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function toggleDict(kind, row, value) {
  try {
    await api.updateDict(kind, row.id, { active: value ? 1 : 0 })
    row.active = value ? 1 : 0
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function removeDict(kind, row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」？`, '删除', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await api.deleteDict(kind, row.id)
    await loadDicts()
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadCategories() {
  try {
    const res = await api.categories()
    categoryList.value = res.items
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function openCategory(row) {
  categoryForm.id = row?.id || null
  categoryForm.name = row?.name || ''
  categoryForm.prefix = row?.prefix || ''
  categoryVisible.value = true
}

async function saveCategory() {
  if (!categoryForm.name.trim() || !categoryForm.prefix.trim()) {
    ElMessage.warning('请填写分类名称和编号前缀')
    return
  }
  submitting.value = true
  try {
    if (categoryForm.id) {
      await api.updateCategory(categoryForm.id, {
        name: categoryForm.name.trim(), prefix: categoryForm.prefix.trim(),
      })
    } else {
      await api.createCategory({
        name: categoryForm.name.trim(), prefix: categoryForm.prefix.trim(),
      })
    }
    ElMessage.success('保存成功')
    categoryVisible.value = false
    await loadCategories()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function removeCategory(row) {
  try {
    await ElMessageBox.confirm(`确定删除分类「${row.name}」？`, '删除分类', { type: 'warning' })
  } catch (e) {
    return
  }
  try {
    await api.deleteCategory(row.id)
    await loadCategories()
    ElMessage.success('已删除')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadSettings() {
  try {
    const s = await api.settings()
    baseUrl.value = s.public_base_url
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function saveBase() {
  saving.value = true
  try {
    await api.saveSettings({ public_base_url: baseUrl.value.trim() })
    ElMessage.success('已保存，请重新打印二维码标签')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await api.users()
    users.value = isAdmin.value ? res.items : res.items.filter((u) => (u.roles || [u.role]).includes('engineer'))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(createForm, {
    name: '', username: '', roles: ['engineer'], phone: '', email: '', password: '',
  })
  createVisible.value = true
}

async function doCreate() {
  if (!createForm.name || !createForm.username || !createForm.password) {
    ElMessage.warning('请填写姓名、登录名和初始密码')
    return
  }
  if (!createForm.roles.length) {
    ElMessage.warning('请至少选择一个角色')
    return
  }
  submitting.value = true
  try {
    await api.createUser({ ...createForm, role: createForm.roles[0] })
    ElMessage.success('账号已创建')
    createVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

function openEditUser(row) {
  Object.assign(editUserForm, {
    id: row.id, name: row.name, phone: row.phone || '',
    email: row.email || '', roles: [...(row.roles || [row.role])],
  })
  editUserVisible.value = true
}

function roleName(r) {
  return { admin: '系统管理员', dispatcher: '受理员', engineer: '工程师' }[r] || r
}

async function saveUser() {
  if (!editUserForm.name) {
    ElMessage.warning('请填写姓名')
    return
  }
  submitting.value = true
  try {
    if (!editUserForm.roles.length) {
      ElMessage.warning('请至少选择一个角色')
      return
    }
    await api.updateUser(editUserForm.id, {
      name: editUserForm.name, phone: editUserForm.phone,
      email: editUserForm.email, roles: editUserForm.roles,
    })
    ElMessage.success('已保存')
    editUserVisible.value = false
    await loadUsers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function loadEmail() {
  try {
    const cfg = await api.emailSettings()
    Object.assign(mail, cfg, { enabled: !!cfg.mail_enabled, smtp_password: '' })
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function saveMail() {
  saving.value = true
  try {
    await api.saveEmailSettings({
      smtp_host: mail.smtp_host, smtp_port: mail.smtp_port,
      smtp_secure: mail.smtp_secure, smtp_user: mail.smtp_user,
      smtp_password: mail.smtp_password, mail_from: mail.mail_from,
      mail_from_name: mail.mail_from_name, mail_enabled: mail.enabled ? 1 : 0,
    })
    ElMessage.success('邮件配置已保存')
    await loadEmail()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function sendTest() {
  if (!testTo.value) {
    ElMessage.warning('请填写接收测试邮件的邮箱')
    return
  }
  testing.value = true
  try {
    await api.testEmail(testTo.value.trim())
    ElMessage.success('测试邮件已发送，请查收')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    testing.value = false
  }
}

function openReset(row) {
  resetUser.value = row
  resetPassword.value = ''
  resetVisible.value = true
}

async function doReset() {
  if (resetPassword.value.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  submitting.value = true
  try {
    await api.updateUser(resetUser.value.id, { password: resetPassword.value })
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row, value) {
  try {
    await api.updateUser(row.id, { active: value ? 1 : 0 })
    row.active = value ? 1 : 0
    ElMessage.success(value ? '已启用' : '已停用')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
</style>
