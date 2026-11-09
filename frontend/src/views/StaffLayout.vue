<template>
  <div class="staff-shell">
    <aside class="staff-aside">
      <div class="aside-brand">
        <div class="brand-mark">运</div>
        <span class="label">运维管理</span>
      </div>
      <nav class="aside-menu">
        <router-link
          v-for="item in menus"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon :size="17"><component :is="item.icon" /></el-icon>
          <span class="label">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="aside-foot">
        <span>运维管理系统 v1.0</span>
      </div>
    </aside>

    <div class="staff-main">
      <header class="staff-topbar">
        <div class="crumb">{{ pageTitle }}</div>
        <div class="topbar-right">
          <el-tag v-if="auth.staff?.on_duty && !hasRole(auth.staff, 'dispatcher') && !hasRole(auth.staff, 'admin')" size="small" effect="dark" type="warning">
            值班受理中
          </el-tag>
          <el-tag size="small" effect="plain" type="info">{{ auth.staff?.role_text }}</el-tag>
          <div class="user-pill">
            <div class="avatar">{{ auth.staff?.name?.slice(0, 1) }}</div>
            <span>{{ auth.staff?.name }}</span>
          </div>
          <el-button link :icon="SwitchButton" @click="logout">退出</el-button>
        </div>
      </header>
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Box, Calendar, Cpu, DataAnalysis, Grid, Monitor, Odometer, Setting, SwitchButton, Tickets } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth, clearAuth, ensureAuth } from '../store'
import { canDispatch, hasRole } from '../utils'

const route = useRoute()
const router = useRouter()

onMounted(() => ensureAuth())

const menus = computed(() => {
  const list = [
    { path: '/admin', label: '工作台', icon: Odometer },
    { path: '/admin/tickets', label: '工单管理', icon: Tickets },
    { path: '/admin/materials', label: '物资管理', icon: Box },
    { path: '/admin/assets', label: '设备台账', icon: Cpu },
    { path: '/admin/rooms', label: '房间与二维码', icon: Grid },
  ]
  if (canDispatch(auth.staff)) {
    list.push({ path: '/board', label: '报障大屏', icon: Monitor })
  }
  if (hasRole(auth.staff, 'admin') || hasRole(auth.staff, 'dispatcher')) {
    list.push({ path: '/admin/reports', label: '运维报表', icon: DataAnalysis })
    list.push({ path: '/admin/duty', label: '值班排班', icon: Calendar })
    list.push({ path: '/admin/settings', label: '系统设置', icon: Setting })
  }
  return list
})

const titles = {
  '/board': '报障大屏',
  '/admin': '工作台',
  '/admin/tickets': '工单管理',
  '/admin/materials': '物资管理',
  '/admin/assets': '设备台账',
  '/admin/rooms': '房间与二维码',
  '/admin/reports': '运维报表',
  '/admin/duty': '值班排班',
  '/admin/settings': '系统设置',
}
const pageTitle = computed(() => titles[route.path] || '运维管理')

function isActive(path) {
  if (path === '/board') return route.path === '/board'
  return path === '/admin' ? route.path === '/admin' : route.path.startsWith(path)
}

async function logout() {
  try {
    await api.logout()
  } catch (e) {
    /* ignore */
  }
  clearAuth()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>
