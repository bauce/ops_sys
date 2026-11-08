<template>
  <div class="home-page">
    <div class="home-wrap">
      <div class="home-hero">
        <div class="brand" style="justify-content: center">
          <div class="brand-mark">运</div>
          <span>信息化运维管理系统</span>
        </div>
        <h1>设备有问题，扫码就能报</h1>
        <p>每个房间门旁都贴有报障二维码，扫码后地点自动带入，无需登录</p>
      </div>

      <div class="entry-grid">
        <div class="entry-card" @click="$router.push('/mine')">
          <div class="entry-icon"><el-icon :size="22"><Tickets /></el-icon></div>
          <h3>我的报障</h3>
          <p>查看已提交的报障进度、确认维修完成</p>
        </div>
        <div class="entry-card" @click="$router.push('/admin')">
          <div class="entry-icon"><el-icon :size="22"><Tools /></el-icon></div>
          <h3>运维人员入口</h3>
          <p>受理报障、上门处理、物资出入库管理</p>
        </div>
      </div>

      <div class="pub-footer">
        <div>首次报障时请填写真实联系人与电话，便于运维人员上门联系</div>
        <div>技术支持：信息中心</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Tickets, Tools } from '@element-plus/icons-vue'
</script>
