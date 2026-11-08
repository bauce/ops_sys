<template>
  <div class="sign-wrap">
    <canvas
      ref="canvas"
      class="sign-canvas"
      @pointerdown="startDraw"
      @pointermove="draw"
      @pointerup="endDraw"
      @pointercancel="endDraw"
      @pointerleave="endDraw"
    ></canvas>
    <div class="sign-bar">
      <span class="muted" style="font-size: 12px">请在框内手写签名</span>
      <el-button size="small" link type="primary" @click="clear">清除重签</el-button>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const canvas = ref(null)
const hasInk = ref(false)
let ctx = null
let drawing = false
let dpr = 1

function setup() {
  const el = canvas.value
  if (!el) return
  dpr = window.devicePixelRatio || 1
  const rect = el.getBoundingClientRect()
  el.width = Math.floor(rect.width * dpr)
  el.height = Math.floor(rect.height * dpr)
  ctx = el.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.lineWidth = 2.2
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = '#1f2937'
  ctx.fillStyle = 'transparent'
  hasInk.value = false
}

function pos(e) {
  const rect = canvas.value.getBoundingClientRect()
  return { x: e.clientX - rect.left, y: e.clientY - rect.top }
}

function startDraw(e) {
  if (!ctx) return
  e.preventDefault()
  drawing = true
  canvas.value.setPointerCapture?.(e.pointerId)
  const p = pos(e)
  ctx.beginPath()
  ctx.moveTo(p.x, p.y)
}

function draw(e) {
  if (!drawing || !ctx) return
  e.preventDefault()
  const p = pos(e)
  ctx.lineTo(p.x, p.y)
  ctx.stroke()
  hasInk.value = true
}

function endDraw() {
  drawing = false
}

function clear() {
  if (!ctx) return
  const el = canvas.value
  ctx.clearRect(0, 0, el.width / dpr, el.height / dpr)
  hasInk.value = false
}

function toDataURL() {
  if (!hasInk.value) return ''
  return canvas.value.toDataURL('image/png')
}

function resize() {
  const url = toDataURL()
  setup()
  if (url && ctx) {
    const img = new Image()
    img.onload = () => ctx.drawImage(img, 0, 0, canvas.value.width / dpr, canvas.value.height / dpr)
    img.src = url
  }
}

let observer = null
onMounted(() => {
  setup()
  observer = new ResizeObserver(() => {
    const el = canvas.value
    if (!el) return
    const width = el.getBoundingClientRect().width
    if (width > 0 && Math.abs(width * dpr - el.width) > 2) resize()
  })
  if (canvas.value) observer.observe(canvas.value)
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  window.removeEventListener('resize', resize)
})

defineExpose({ clear, toDataURL })
</script>

<style scoped>
.sign-wrap {
  border: 1px dashed #c7d2e5;
  border-radius: 10px;
  background: #fbfdff;
  overflow: hidden;
}
.sign-canvas {
  display: block;
  width: 100%;
  height: 170px;
  touch-action: none;
  cursor: crosshair;
}
.sign-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px 6px;
  border-top: 1px dashed #e2e8f3;
}
</style>
