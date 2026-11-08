<template>
  <div v-if="ticket">
    <div class="detail-head">
      <div>
        <div style="font-size: 16px; font-weight: 650">{{ ticket.device }}</div>
        <div class="detail-code">{{ ticket.code }} · 提交于 {{ fmtTime(ticket.created_at) }}</div>
      </div>
      <el-tag :type="statusMeta(ticket.status).type" effect="light">
        <span class="status-dot" :style="{ background: statusMeta(ticket.status).color }"></span>
        {{ ticket.status_text }}
      </el-tag>
    </div>

    <div class="info-grid">
      <div class="info-item">
        <div class="k">报障地点</div>
        <div class="v">{{ ticket.location }}</div>
      </div>
      <div class="info-item">
        <div class="k">故障类型</div>
        <div class="v">{{ ticket.fault_type }}</div>
      </div>
      <div class="info-item">
        <div class="k">联系人</div>
        <div class="v">{{ ticket.contact_name }} · {{ ticket.contact_phone }}</div>
      </div>
      <div class="info-item">
        <div class="k">处理人</div>
        <div class="v">{{ ticket.assignee_name || '待指派' }}</div>
      </div>
      <div class="info-item">
        <div class="k">期望上门时间</div>
        <div class="v">{{ ticket.expect_time || '立即上门' }}</div>
      </div>
      <div v-if="ticket.finished_at" class="info-item">
        <div class="k">处理完成时间</div>
        <div class="v">{{ fmtTime(ticket.finished_at) }}</div>
      </div>
      <div v-if="ticket.confirm_at" class="info-item">
        <div class="k">确认时间</div>
        <div class="v">{{ fmtTime(ticket.confirm_at) }}</div>
      </div>
    </div>

    <template v-if="ticket.description">
      <div style="font-size: 12px; color: var(--ink-3); margin: 12px 0 6px">故障描述</div>
      <div class="note-box">{{ ticket.description }}</div>
    </template>

    <template v-if="ticket.photos && ticket.photos.length">
      <div style="font-size: 12px; color: var(--ink-3); margin: 12px 0 6px">现场照片</div>
      <div class="photo-list">
        <el-image
          v-for="(p, i) in ticket.photos"
          :key="i"
          :src="p"
          :preview-src-list="ticket.photos"
          :initial-index="i"
          fit="cover"
          class="photo-thumb"
        />
      </div>
    </template>

    <template v-if="ticket.fault_cause">
      <div style="font-size: 12px; color: var(--ink-3); margin: 12px 0 6px">故障原因</div>
      <div class="note-box">{{ ticket.fault_cause }}</div>
    </template>

    <template v-if="ticket.solve_note">
      <div style="font-size: 12px; color: var(--ink-3); margin: 12px 0 6px">处理说明</div>
      <div class="note-box">{{ ticket.solve_note }}</div>
    </template>

    <template v-if="ticket.materials && ticket.materials.length">
      <div style="font-size: 12px; color: var(--ink-3); margin: 14px 0 6px">领用物资</div>
      <el-table :data="ticket.materials" size="small" border>
        <el-table-column prop="material_name" label="物资" />
        <el-table-column prop="spec" label="规格" show-overflow-tooltip />
        <el-table-column label="数量" width="90" align="center">
          <template #default="{ row }">{{ row.qty }} {{ row.unit }}</template>
        </el-table-column>
      </el-table>
    </template>

    <template v-if="ticket.rating">
      <div style="font-size: 12px; color: var(--ink-3); margin: 14px 0 6px">服务评价</div>
      <div class="gap-8">
        <el-rate :model-value="ticket.rating" disabled />
        <span class="muted" style="font-size: 12.5px">{{ ticket.confirm_comment }}</span>
      </div>
    </template>

    <template v-if="ticket.signature">
      <div style="font-size: 12px; color: var(--ink-3); margin: 14px 0 6px">报障人签字</div>
      <img
        :src="ticket.signature"
        alt="签名"
        style="max-width: 240px; width: 60%; border: 1px solid var(--line); border-radius: 8px; background: #fff"
      />
    </template>

    <template v-if="ticket.logs && ticket.logs.length">
      <div style="font-size: 12px; color: var(--ink-3); margin: 16px 0 10px">处理进度</div>
      <div class="timeline-wrap">
        <el-timeline>
          <el-timeline-item
            v-for="(log, i) in ticket.logs"
            :key="i"
            :timestamp="fmtTime(log.created_at)"
            placement="top"
            :color="i === ticket.logs.length - 1 ? '#2f6feb' : '#c9d6ea'"
          >
            <div style="font-size: 13px; font-weight: 600">{{ log.action }}</div>
            <div class="muted" style="font-size: 12.5px">{{ log.actor }}<span v-if="log.note"> · {{ log.note }}</span></div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </template>

    <div v-if="showActions" style="margin-top: 18px; display: flex; gap: 8px">
      <el-button
        v-if="ticket.status === 'pending' && ticket.is_owner"
        @click="$emit('cancel')"
      >
        撤销报障
      </el-button>
      <el-button
        v-if="ticket.status === 'pending_confirm'"
        type="primary"
        @click="$emit('confirm')"
      >
        确认维修完成
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { fmtTime, statusMeta } from '../utils'

defineProps({
  ticket: { type: Object, default: null },
  showActions: { type: Boolean, default: false },
})
defineEmits(['confirm', 'cancel'])
</script>

<style scoped>
.photo-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.photo-thumb {
  width: 92px;
  height: 92px;
  border-radius: 8px;
  border: 1px solid var(--line);
  cursor: zoom-in;
}
</style>
