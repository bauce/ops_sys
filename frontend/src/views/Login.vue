<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <div class="brand-mark">运</div>
        <span>信息化运维管理系统</span>
      </div>
      <div class="login-title">运维人员登录</div>
      <div class="login-sub">报障受理 · 上门处理 · 物资出入库</div>

      <div v-if="testMode" class="test-panel">
        <div class="test-head">
          <span class="test-badge">测试环境</span>
          <span class="test-title">免密登录</span>
        </div>
        <div class="test-sub">点击账号直接进入，无需输入密码</div>
        <div class="test-accounts">
          <button
            v-for="a in accounts"
            :key="a.username"
            class="test-account"
            :disabled="!!quickLoading"
            @click="quickLogin(a)"
          >
            <span class="ta-name">{{ a.name }}</span>
            <span class="ta-role">{{ a.role_text || a.username }}</span>
          </button>
        </div>
        <el-divider>或输入账号</el-divider>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" size="large" placeholder="请输入账号" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            show-password
            :placeholder="testMode ? '测试环境可留空' : '请输入密码'"
            :prefix-icon="Lock"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%; height: 44px" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>

      <div style="text-align: center; margin-top: 16px; color: #909399; font-size: 12px">
        {{ testMode ? '测试环境已开启免密登录，点击上方账号即可进入' : '账号由系统管理员分配，忘记密码请联系管理员重置' }}
      </div>

      <div style="text-align: center; margin-top: 14px">
        <el-button link @click="$router.push('/')">← 返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { api } from '../api'
import { setStaff } from '../store'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const quickLoading = ref('')
const formRef = ref(null)
const testMode = ref(false)
const accounts = ref([])
const form = reactive({ username: '', password: '' })
const rules = computed(() => ({
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: testMode.value ? [] : [{ required: true, message: '请输入密码', trigger: 'blur' }],
}))

onMounted(async () => {
  try {
    const data = await api.loginOptions()
    testMode.value = !!data.test_mode
    accounts.value = data.accounts || []
  } catch (e) {
    testMode.value = false
  }
})

function afterLogin(staff) {
  setStaff(staff)
  ElMessage.success(`欢迎回来，${staff.name}`)
  router.push(route.query.redirect || '/admin')
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  loading.value = true
  try {
    afterLogin(await api.login(form.username.trim(), form.password))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function quickLogin(account) {
  quickLoading.value = account.username
  try {
    afterLogin(await api.login(account.username, ''))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    quickLoading.value = ''
  }
}
</script>

<style scoped>
.test-panel {
  margin: 18px 0 6px;
  padding: 14px;
  border: 1px solid #d9e6fb;
  border-radius: 10px;
  background: #f5f9ff;
}
.test-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.test-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: #2f6feb;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.test-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}
.test-sub {
  margin-top: 4px;
  color: #8a94a6;
  font-size: 12px;
}
.test-accounts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.test-account {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 9px 12px;
  border: 1px solid #e4e9f2;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.test-account:hover {
  border-color: #2f6feb;
  box-shadow: 0 2px 8px rgba(47, 111, 235, 0.12);
}
.test-account:disabled {
  opacity: 0.6;
  cursor: default;
}
.ta-name {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}
.ta-role {
  font-size: 10px;
  color: #8a94a6;
}
</style>
