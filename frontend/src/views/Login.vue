<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <div class="brand-mark">运</div>
        <span>信息化运维管理系统</span>
      </div>
      <div class="login-title">运维人员登录</div>
      <div class="login-sub">报障受理 · 上门处理 · 物资出入库</div>

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
            placeholder="请输入密码"
            :prefix-icon="Lock"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%; height: 44px" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>

      <div style="text-align: center; margin-top: 16px; color: #909399; font-size: 12px">
        账号由系统管理员分配，忘记密码请联系管理员重置
      </div>

      <div style="text-align: center; margin-top: 14px">
        <el-button link @click="$router.push('/')">← 返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { api } from '../api'
import { setStaff } from '../store'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const formRef = ref(null)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  loading.value = true
  try {
    const staff = await api.login(form.username.trim(), form.password)
    setStaff(staff)
    ElMessage.success(`欢迎回来，${staff.name}`)
    router.push(route.query.redirect || '/admin')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>
