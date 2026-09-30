<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getJSON, postJSON } from '../api'

const items = ref([])
const err = ref('')
const busyId = ref(null)
const confirmingId = ref(null)
const router = useRouter()

async function load() {
  err.value = ''
  try {
    items.value = (await getJSON('/api/runs')).items
  } catch (e) {
    err.value = String(e.message || e)
  }
}

onMounted(load)

async function issue(r) {
  err.value = ''
  busyId.value = r.id
  try {
    const lab = await postJSON(`/api/runs/${r.id}/labels`, {})
    await router.push(`/labels/${lab.id}`)
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busyId.value = null
  }
}

async function voidRun(r) {
  err.value = ''
  busyId.value = r.id
  try {
    await postJSON(`/api/runs/${r.id}/void`, {})
    confirmingId.value = null
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div class="page">
    <h1>用纸档</h1>
    <p class="lede">算纸页「写入用纸档」后的落库结果，按次保留盒名与面积。未作废的用纸档可出裁切签。</p>
    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">还没有写入过。先去算纸试一单。</p>
    <ul v-else class="item-list">
      <li v-for="r in items" :key="r.id">
        <span>
          <router-link :to="`/runs/${r.id}`">{{ r.box_name || '盒已缺失' }}</router-link>
          <span class="pill" :class="{ warn: r.voided }" style="margin-left:0.6rem">
            {{ r.voided ? '已作废' : '在用' }}
          </span>
        </span>
        <span class="meta">
          {{ r.result?.paper_m2 ?? '—' }} m²
          <template v-if="!r.voided">
            <button class="sm" style="margin-left:0.7rem" :disabled="busyId === r.id" @click="issue(r)">出签</button>
            <template v-if="confirmingId === r.id">
              <button class="sm ribbon" :disabled="busyId === r.id" @click="voidRun(r)">确认作废</button>
              <button class="sm ghost" :disabled="busyId === r.id" @click="confirmingId = null">取消</button>
            </template>
            <button v-else class="sm ghost" :disabled="busyId === r.id" @click="confirmingId = r.id">作废</button>
          </template>
        </span>
      </li>
    </ul>
  </div>
</template>
