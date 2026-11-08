<template>
  <div class="pub-page">
    <div class="pub-topbar">
      <div class="brand">
        <div class="brand-mark">运</div>
        <span>信息化运维</span>
      </div>
      <el-button link type="primary" @click="$router.push('/mine')">我的报障</el-button>
    </div>

    <div class="pub-wrap">
      <div class="security-notice">
        <div class="sn-icon">!</div>
        <div>
          <div class="sn-title">非涉密系统，严禁上传涉密信息</div>
          <div class="sn-text">
            本系统仅用于非涉密设备报障，请勿填写或上传国家秘密、工作秘密、内部敏感信息等涉密内容。
          </div>
        </div>
      </div>

      <div v-if="error" class="pub-card" style="text-align: center; padding: 36px 20px">
        <div style="font-size: 40px">⚠️</div>
        <h3 style="margin: 12px 0 6px">二维码无效</h3>
        <p class="muted" style="font-size: 13px">{{ error }}</p>
        <el-button type="primary" style="margin-top: 14px" @click="$router.push('/')">返回首页</el-button>
      </div>

      <template v-else>
        <div v-if="selectedRoom" class="pub-hero">
          <div class="loc">{{ selectedRoom.building }}{{ selectedRoom.floor }}层 {{ selectedRoom.room_no }}室</div>
          <div class="name">{{ selectedRoom.name || '报障点' }}</div>
          <div v-if="isScannedRoom && recent" class="recent">
            <span>📍</span>
            <span>近 30 天该房间报障 {{ recent }} 次</span>
          </div>
        </div>

        <!-- 提交成功 -->
        <div v-if="submitted" class="pub-card" style="text-align: center; padding: 30px 20px">
          <el-result icon="success" title="报障已提交">
            <template #sub-title>
              <div style="line-height: 2">
                单号：<b class="mono">{{ submitted.code }}</b><br />
                {{ submitted.location }}<br />
                期望上门：{{ submitted.expect_time }}<br />
                运维人员受理后会电话联系您，请保持电话畅通
              </div>
            </template>
            <template #extra>
              <el-button type="primary" @click="$router.push('/mine')">查看报障进度</el-button>
              <el-button @click="resetForm">再报一单</el-button>
            </template>
          </el-result>
        </div>

        <!-- 报障表单 -->
        <div v-else class="pub-card">
          <h3>设备故障报障</h3>
          <p class="pub-hint">请填写故障信息，带 * 为必填项</p>
          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
            <el-form-item label="报障地点" prop="room_id">
              <el-select v-model="form.room_id" size="large" filterable placeholder="请选择报障地点" style="width: 100%">
                <el-option
                  v-for="r in rooms"
                  :key="r.id"
                  :label="r.location"
                  :value="r.id"
                />
              </el-select>
              <div class="field-tip">默认是扫码所在位置，如您在其他地点办公，可切换为实际故障地点</div>
            </el-form-item>

            <el-form-item label="故障设备" prop="device">
              <el-input
                v-model="form.device"
                size="large"
                maxlength="60"
                placeholder="如：前台电脑、打印机、投影仪"
                clearable
              />
              <div v-if="quickDevices.length" class="quick-chips" style="margin-top: 10px">
                <span class="chip" v-for="d in quickDevices" :key="d" @click="form.device = d">{{ d }}</span>
              </div>
            </el-form-item>

            <el-form-item label="故障类型" prop="fault_type">
              <el-select v-model="form.fault_type" size="large" placeholder="请选择故障类型" style="width: 100%">
                <el-option v-for="t in faultTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>

            <el-form-item label="期待上门时间">
              <div style="width: 100%">
                <el-radio-group v-model="form.expect_mode" size="large" class="expect-group">
                  <el-radio-button value="asap">立即上门</el-radio-button>
                  <el-radio-button value="custom">指定时间</el-radio-button>
                </el-radio-group>
                <div v-if="form.expect_mode === 'custom'" style="margin-top: 10px">
                  <el-date-picker
                    v-model="form.expect_time"
                    type="datetime"
                    size="large"
                    placeholder="选择期望上门的时间点"
                    format="YYYY-MM-DD HH:mm"
                    :disabled-date="disabledDate"
                    style="width: 100%"
                  />
                </div>
                <div class="field-tip">
                  {{ form.expect_mode === 'asap' ? '受理后尽快安排上门' : '默认今天，可直接调整时间，也可更改日期' }}
                </div>
              </div>
            </el-form-item>

            <el-form-item label="故障描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="3"
                maxlength="500"
                show-word-limit
                placeholder="简单描述故障现象，如：电脑开机黑屏、网络连不上"
              />
            </el-form-item>

            <el-form-item label="现场照片（选填，最多 3 张）">
              <div style="width: 100%">
                <div class="photo-grid">
                  <div v-for="(p, i) in form.photos" :key="i" class="photo-item">
                    <img :src="p" alt="现场照片" />
                    <span class="photo-del" @click="form.photos.splice(i, 1)">×</span>
                  </div>
                  <div v-if="form.photos.length < 3" class="photo-add" @click="pickPhotos">
                    <span class="plus">＋</span>
                    <span>拍照/上传</span>
                  </div>
                </div>
                <input
                  ref="photoInput"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  multiple
                  style="display: none"
                  @change="onPhotos"
                />
                <div class="field-tip">可拍摄设备故障现场，便于运维人员提前判断；请勿拍摄涉密文件、屏幕或场所</div>
              </div>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :xs="24" :sm="12">
                <el-form-item label="联系人" prop="contact_name">
                  <el-input v-model="form.contact_name" size="large" maxlength="20" placeholder="您的姓名" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="联系电话" prop="contact_phone">
                  <el-input v-model="form.contact_phone" size="large" maxlength="20" placeholder="便于上门联系" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-button
              type="primary"
              size="large"
              style="width: 100%; height: 46px; margin-top: 4px"
              :loading="submitting"
              @click="submit"
            >
              提交报障
            </el-button>
          </el-form>
        </div>
      </template>

      <div class="pub-footer">
        <div>同一手机号提交的单，可在「我的报障」输入后四位随时查询</div>
        <div>维修完成后请报障人本人确认并手写签名</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const scannedRoom = ref(null)
const recent = ref(0)
const rooms = ref([])
const devices = ref([])
const faultTypes = ref([])
const error = ref('')
const submitting = ref(false)
const submitted = ref(null)
const formRef = ref(null)

const form = reactive({
  room_id: null,
  device: '',
  fault_type: '',
  description: '',
  contact_name: '',
  contact_phone: '',
  expect_mode: 'asap',
  expect_time: null,
  photos: [],
})

const rules = {
  room_id: [{ required: true, message: '请选择报障地点', trigger: 'change' }],
  device: [{ required: true, message: '请填写故障设备', trigger: 'blur' }],
  fault_type: [{ required: true, message: '请选择故障类型', trigger: 'change' }],
  contact_name: [{ required: true, message: '请填写联系人', trigger: 'blur' }],
  contact_phone: [
    { required: true, message: '请填写联系电话', trigger: 'blur' },
    { pattern: /^[0-9\-+\s]{6,20}$/, message: '电话格式不正确', trigger: 'blur' },
  ],

}

const qr = route.params.qr
const selectedRoom = computed(() => rooms.value.find((r) => r.id === form.room_id) || null)
const isScannedRoom = computed(() => scannedRoom.value && form.room_id === scannedRoom.value.id)
const quickDevices = computed(() => devices.value.slice(0, 8))

onMounted(async () => {
  try {
    const [info, meta] = await Promise.all([api.room(qr), api.meta()])
    scannedRoom.value = info.room
    recent.value = info.recent_30d
    rooms.value = meta.rooms
    devices.value = meta.devices
    faultTypes.value = meta.fault_types
    form.room_id = info.room.id
    document.title = `${info.room.building}${info.room.floor}层${info.room.room_no}室 · 设备报障`
  } catch (e) {
    error.value = e.message
  }
})

const photoInput = ref(null)

function pickPhotos() {
  photoInput.value?.click()
}

function readImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

async function compress(file) {
  const dataUrl = await readImage(file)
  const img = await loadImage(dataUrl)
  const max = 1400
  let { width, height } = img
  if (width > max || height > max) {
    const ratio = Math.min(max / width, max / height)
    width = Math.round(width * ratio)
    height = Math.round(height * ratio)
  }
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0, width, height)
  return canvas.toDataURL('image/jpeg', 0.78)
}

async function onPhotos(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  const room = 3 - form.photos.length
  if (room <= 0) return
  for (const file of files.slice(0, room)) {
    if (!file.type.startsWith('image/')) {
      ElMessage.warning('请选择图片文件')
      continue
    }
    if (file.size > 15 * 1024 * 1024) {
      ElMessage.warning('单张图片不能超过 15MB')
      continue
    }
    try {
      form.photos.push(await compress(file))
    } catch (e) {
      ElMessage.error('图片处理失败，请重试')
    }
  }
}

function defaultCustomTime() {
  const now = new Date()
  const d = new Date(now)
  d.setSeconds(0, 0)
  const m = d.getMinutes()
  if (m < 30) d.setMinutes(30)
  else { d.setHours(d.getHours() + 1); d.setMinutes(0) }
  if (d <= now) d.setMinutes(d.getMinutes() + 30)
  if (d.getDate() !== now.getDate()) {
    const t = new Date(now)
    t.setDate(t.getDate() + 1)
    t.setHours(9, 0, 0, 0)
    return t
  }
  return d
}

watch(
  () => form.expect_mode,
  (mode) => {
    if (mode === 'custom' && !form.expect_time) {
      form.expect_time = defaultCustomTime()
    }
  }
)

function pad(n) {
  return String(n).padStart(2, '0')
}

function expectText() {
  if (form.expect_mode === 'asap') return '立即上门'
  const d = form.expect_time ? new Date(form.expect_time) : null
  if (!d) return ''
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function disabledDate(date) {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const end = new Date(start)
  end.setDate(end.getDate() + 30)
  return date < start || date > end
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  if (form.expect_mode === 'custom') {
    if (!form.expect_time) {
      ElMessage.warning('请选择指定的上门时间')
      return
    }
    if (new Date(form.expect_time).getTime() < Date.now() - 60000) {
      ElMessage.warning('上门时间不能早于当前时间')
      return
    }
  }
  submitting.value = true
  try {
    const res = await api.createTicket({
      qr,
      room_id: form.room_id,
      device: form.device,
      fault_type: form.fault_type,
      description: form.description,
      contact_name: form.contact_name,
      contact_phone: form.contact_phone,
      expect_time: expectText(),
      photos: form.photos,
    })
    submitted.value = res
    ElMessage.success('提交成功')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  submitted.value = null
  form.device = ''
  form.fault_type = ''
  form.description = ''
  form.expect_mode = 'asap'
  form.expect_time = null
  form.photos = []
}
</script>

<style scoped>
.security-notice {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: #fff8e8;
  border: 1px solid #f0d9a8;
  color: #8a6416;
  border-radius: 12px;
  padding: 11px 14px;
  margin-bottom: 14px;
}
.sn-icon {
  flex: 0 0 20px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e6a23c;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  display: grid;
  place-items: center;
  margin-top: 1px;
}
.sn-title {
  font-size: 13.5px;
  font-weight: 700;
}
.sn-text {
  font-size: 12px;
  line-height: 1.7;
  color: #a1731a;
}

.field-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin-top: 6px;
}

.photo-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.photo-item {
  position: relative;
  width: 92px;
  height: 92px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--line);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.photo-del {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 14px;
  cursor: pointer;
}

.photo-add {
  width: 92px;
  height: 92px;
  border-radius: 10px;
  border: 1px dashed #c7d2e5;
  background: #f8fafd;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--ink-3);
  font-size: 12px;
  cursor: pointer;
}

.photo-add:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.photo-add .plus {
  font-size: 22px;
  line-height: 1;
}

.expect-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.expect-group :deep(.el-radio-button__inner) {
  border-radius: 8px !important;
  border-left: 1px solid var(--el-border-color);
}

.expect-group :deep(.el-radio-button) {
  margin: 0;
}
</style>
