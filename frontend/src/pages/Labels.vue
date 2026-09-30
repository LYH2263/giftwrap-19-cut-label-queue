<script setup>
import { onMounted, ref, watch } from 'vue'
import { getJSON } from '../api'

const items = ref([])
const filter = ref('all')
const err = ref('')

async function load() {
  err.value = ''
  try {
    const q = filter.value === 'all' ? '' : `?status=${filter.value}`
    items.value = (await getJSON(`/api/labels${q}`)).items
  } catch (e) {
    err.value = String(e.message || e)
  }
}

onMounted(load)
watch(filter, load)
</script>

<template>
  <div class="page">
    <h1>裁切签队列</h1>
    <p class="lede">每支签的盒名、用纸量、丝带长与校验和都在出签瞬间冻结；之后改盒边或折边不影响已出签面。</p>
    <div class="row">
      <select v-model="filter">
        <option value="all">全部状态</option>
        <option value="queued">queued 待打印</option>
        <option value="printed">printed 已打印</option>
      </select>
    </div>
    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">队列里还没有签。去用纸档对一条记录「出签」。</p>
    <ul v-else class="item-list label-list">
      <li v-for="l in items" :key="l.id">
        <router-link class="label-main" :to="`/labels/${l.id}`">
          <span class="label-no">{{ l.face.label_no }}</span>
          <span class="label-face">
            <strong>{{ l.face.box_name }}</strong>
            <span class="meta">{{ l.face.paper_m2 }} m² · 丝带 {{ l.face.ribbon_m ?? '—' }} m</span>
            <code class="cs">{{ l.checksum }}</code>
          </span>
        </router-link>
        <span class="meta label-side">
          <span v-if="l.voided" class="pill warn">原档已作废</span>
          <span class="pill" :class="{ done: l.status === 'printed' }">
            {{ l.status === 'printed' ? 'printed' : 'queued' }}
          </span>
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.label-main {
  display: inline-flex;
  align-items: baseline;
  gap: 0.75rem;
  text-decoration: none;
  color: var(--ink);
}
.label-no {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--wash-b);
  min-width: 2.4rem;
}
.label-face {
  display: inline-flex;
  flex-direction: column;
  gap: 0.15rem;
}
.label-side {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
}
.cs {
  font-size: 0.74rem;
  word-break: break-all;
  background: rgba(20, 32, 51, 0.06);
  padding: 0.12rem 0.4rem;
  border-radius: var(--radius);
  max-width: 34rem;
}
.pill.done {
  background: rgba(184, 151, 59, 0.16);
  color: var(--foil);
}
</style>
