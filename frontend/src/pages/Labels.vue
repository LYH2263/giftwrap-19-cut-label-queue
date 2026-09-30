<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'

const items = ref([])
const err = ref('')

onMounted(async () => {
  try {
    items.value = (await getJSON('/api/labels')).items
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>

<template>
  <div class="page">
    <h1>裁切签队列</h1>
    <p class="lede">签面字段钉在出签瞬间的快照上，与现场盒型/折边主数据互不影响。</p>
    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">
      还没有出签。去 <router-link to="/history">用纸档</router-link> 出一张。
    </p>
    <ul v-else class="item-list">
      <li v-for="l in items" :key="l.id">
        <span>
          <router-link :to="`/labels/${l.id}`">签 #{{ l.id }}</router-link>
          <span style="margin-left:0.7rem">{{ l.box_name || '盒已缺失' }}</span>
          <span v-if="l.run_voided" class="pill warn" style="margin-left:0.6rem">用纸档已作废</span>
        </span>
        <span class="meta">
          {{ l.paper_m2 ?? '—' }} m² · 丝带 {{ l.ribbon_m ?? '—' }} m
          <span class="pill" :class="{ done: l.status === 'printed' }" style="margin-left:0.6rem">
            {{ l.status === 'printed' ? '已打印' : '待打印' }}
          </span>
          <router-link :to="`/runs/${l.run_id}`" style="margin-left:0.7rem">用纸档 #{{ l.run_id }}</router-link>
        </span>
      </li>
    </ul>
  </div>
</template>
