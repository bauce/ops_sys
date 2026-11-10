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

    <el-drawer v-model="drawerOpen" direction="ltr" size="78%" :with-header="false" class="mobile-nav-drawer">
      <div class="m-drawer-brand">
        <div class="brand-mark">运</div>
        <div>
          <div style="font-weight: 700; color: #1f2937">运维管理</div>
          <div style="font-size: 11px; color: #8a94a6">信息化运维管理系统</div>
        </div>
      </div>
      <nav class="m-drawer-menu">
        <router-link
          v-for="item in menus"
          :key="item.path"
          :to="item.path"
          class="m-nav-item"
          :class="{ active: isActive(item.path) }"
          @click="drawerOpen = false"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="m-drawer-foot">
        <span>{{ auth.staff?.name }} · {{ auth.staff?.role_text }}</span>
        <el-button link type="primary" @click="logout">退出登录</el-button>
      </div>
    </el-drawer>

    <div class="staff-main">
      <header class="staff-topbar">
        <div class="topbar-left">
          <el-button class="mobile-menu-btn" link :icon="Menu" @click="drawerOpen = true" />
          <div class="crumb">{{ pageTitle }}</div>
        </div>
        <div class="topbar-right">
          <el-tag v-if="auth.staff?.on_duty && !hasRole(auth.staff, 'dispatcher') && !hasRole(auth.staff, 'admin')" size="small" effect="dark" type="warning">
            值班受理中
          </el-tag>
          <el-tag class="role-tag" size="small" effect="plain" type="info">{{ auth.staff?.role_text }}</el-tag>
          <div class="user-pill">
            <div class="avatar">{{ auth.staff?.name?.slice(0, 1) }}</div>
            <span class="user-name">{{ auth.staff?.name }}</span>
          </div>
          <el-button class="logout-btn" link :icon="SwitchButton" @click="logout"><span class="logout-text">退出</span></el-button>
        </div>
      </header>
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Box, Calendar, Cpu, DataAnalysis, Grid, Menu, Monitor, Odometer, Setting, SwitchButton, Tickets } from '@element-plus/icons-vue'
import { api } from '../api'
import { auth, clearAuth, ensureAuth } from '../store'
import { canDispatch, hasRole } from '../utils'

const route = useRoute()
const router = useRouter()
const drawerOpen = ref(false)

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

<style scoped>
.mobile-nav-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
}
.m-drawer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 16px;
  border-bottom: 1px solid #eef1f7;
}
.m-drawer-menu {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
}
.m-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  color: #4b5563;
  font-size: 14px;
  text-decoration: none;
  margin-bottom: 4px;
}
.m-nav-item.active {
  background: #eaf1ff;
  color: #2f6feb;
  font-weight: 600;
}
.m-drawer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 18px;
  border-top: 1px solid #eef1f7;
  font-size: 12px;
  color: #8a94a6;
}
</style>
