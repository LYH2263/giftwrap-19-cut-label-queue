<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const items = ref([])
const err = ref('')
const busy = ref(null)

async function load() {
  err.value = ''
  try {
    items.value = (await getJSON('/api/runs')).items
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function issue(r) {
  err.value = ''
  busy.value = `issue-${r.id}`
  try {
    await postJSON(`/api/runs/${r.id}/labels`, {})
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = null
  }
}

async function voidRun(r) {
  if (!window.confirm(`作废用纸档 #${r.id}（${r.box_name}）？作废后不能再出新签，已打印的签仍可查。`)) return
  err.value = ''
  busy.value = `void-${r.id}`
  try {
    await postJSON(`/api/runs/${r.id}/void`, {})
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>用纸档</h1>
    <p class="lede">算纸页「写入用纸档」后的落库结果。未作废的档可「出签」进入裁切签队列；出签不新增用纸档，同一档可多次出签。</p>
    <div class="row">
      <router-link class="btn ghost" to="/labels">查看裁切签队列 →</router-link>
    </div>
    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">还没有写入过。先去算纸试一单。</p>
    <ul v-else class="item-list">
      <li v-for="r in items" :key="r.id" :id="`run-${r.id}`" :class="{ 'is-void': r.voided }">
        <span>
          <a class="run-title">#{{ r.id }} {{ r.box_name }}</a>
          <span class="pill" :class="{ warn: r.voided }">{{ r.voided ? '已作废' : '在用' }}</span>
        </span>
        <span class="meta run-actions">
          {{ r.result?.paper_m2 ?? '—' }} m²
          <button
            class="ribbon"
            :disabled="busy === `issue-${r.id}` || r.voided"
            @click="issue(r)"
          >出签</button>
          <button
            class="ghost"
            :disabled="busy === `void-${r.id}` || r.voided"
            @click="voidRun(r)"
          >作废</button>
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.run-title {
  margin-right: 0.6rem;
}
.is-void .run-title {
  color: var(--ink-soft);
  text-decoration: line-through;
}
.run-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.run-actions button {
  padding: 0.3rem 0.7rem;
  font-size: 0.85rem;
}
</style>
