<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON } from '../api'

const route = useRoute()
const label = ref(null)
const err = ref('')
const busy = ref(false)
const checkOk = ref(null)

// 与后端一致的稳定序列化：键名排序、紧凑分隔、Unicode 原样
function canonical(face) {
  return `{${Object.keys(face).sort().map((k) => `${JSON.stringify(k)}:${canonicalVal(face[k])}`).join(',')}}`
}
function canonicalVal(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v)
  return canonical(v)
}
async function verifyChecksum(face, expected) {
  try {
    const buf = new TextEncoder().encode(canonical(face))
    const digest = await crypto.subtle.digest('SHA-256', buf)
    const hex = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
    checkOk.value = hex === expected
  } catch {
    checkOk.value = null
  }
}

async function load() {
  err.value = ''
  try {
    label.value = await getJSON(`/api/labels/${route.params.id}`)
    await verifyChecksum(label.value.face, label.value.checksum)
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function markPrinted() {
  busy.value = true
  err.value = ''
  try {
    await postJSON(`/api/labels/${route.params.id}/print`, {})
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <p><router-link class="back" to="/labels">← 裁切签队列</router-link></p>
    <h1>签详情</h1>
    <p v-if="err" class="bad">{{ err }}</p>
    <template v-else-if="label">
      <div class="label-card">
        <div class="card-head">
          <span class="label-no">{{ label.face.label_no }}</span>
          <span class="pill" :class="{ done: label.status === 'printed', warn: label.voided }">
            {{ label.status === 'printed' ? 'printed 已打印' : 'queued 待打印' }}
          </span>
          <span v-if="label.voided" class="pill warn">原用纸档已作废 · 本签只读</span>
        </div>

        <dl class="face-grid">
          <div><dt>盒名</dt><dd>{{ label.face.box_name }}</dd></div>
          <div><dt>用纸量</dt><dd>{{ label.face.paper_m2 }} m²</dd></div>
          <div><dt>丝带长</dt><dd>{{ label.face.ribbon_m ?? '—' }} m</dd></div>
          <div><dt>折边系数</dt><dd>{{ label.face.overlap }}</dd></div>
          <div><dt>系带方式</dt><dd>{{ label.face.wrap_style ?? '—' }}</dd></div>
          <div><dt>出签时刻</dt><dd>{{ label.face.issued_at }}</dd></div>
        </dl>

        <div class="checksum">
          <dt>内容校验和 sha256</dt>
          <dd><code>{{ label.checksum }}</code></dd>
          <dd class="verify" v-if="checkOk !== null">
            <span class="pill" :class="{ done: checkOk }">{{ checkOk ? '签面重算一致' : '校验不一致' }}</span>
          </dd>
        </div>
      </div>

      <div class="row actions">
        <button
          class="ribbon"
          :disabled="busy || label.status === 'printed'"
          @click="markPrinted"
        >{{ label.status === 'printed' ? '已打印（不可改回）' : '标记 printed' }}</button>
        <router-link class="btn ghost" :to="`/history#run-${label.run_id}`">回链用纸档 #{{ label.run_id }} →</router-link>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back {
  color: var(--ink-soft);
  text-decoration: none;
  font-size: 0.9rem;
}
.back:hover { color: var(--wash-b); }
.label-card {
  margin-top: 0.5rem;
  padding: 1.4rem 1.5rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(243, 247, 244, 0.9));
}
.card-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 1.1rem;
}
.label-no {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--wash-b);
}
.face-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.9rem 1.2rem;
  margin: 0 0 1.2rem;
}
.face-grid dt, .checksum dt {
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin: 0 0 0.2rem;
}
.face-grid dd, .checksum dd { margin: 0; }
.face-grid dd {
  font-size: 1.05rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.checksum {
  border-top: 1px dashed rgba(184, 151, 59, 0.45);
  padding-top: 1rem;
}
.checksum code {
  word-break: break-all;
  font-size: 0.82rem;
}
.verify { margin-top: 0.5rem; }
.pill.done {
  background: rgba(184, 151, 59, 0.16);
  color: var(--foil);
}
.actions { margin-top: 1.3rem; }
</style>
