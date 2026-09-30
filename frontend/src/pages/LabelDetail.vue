<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const props = defineProps({ id: String })
const lab = ref(null)
const err = ref('')
const busy = ref(false)

async function load() {
  err.value = ''
  try {
    lab.value = await getJSON(`/api/labels/${props.id}`)
  } catch (e) {
    err.value = String(e.message || e)
  }
}

onMounted(load)

async function markPrinted() {
  err.value = ''
  busy.value = true
  try {
    await postJSON(`/api/labels/${props.id}/print`, {})
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <p v-if="err" class="bad">{{ err }}</p>
    <template v-else-if="lab">
      <h1>
        裁切签 #{{ lab.id }}
        <span class="pill" :class="{ done: lab.status === 'printed' }" style="margin-left:0.6rem">
          {{ lab.status === 'printed' ? '已打印' : '待打印' }}
        </span>
      </h1>
      <p class="lede">盒名 / 用纸 / 丝带均取自出签瞬间的用纸档快照；checksum 钉死签面正文。</p>
      <p v-if="lab.run_voided" class="pill warn" style="margin-bottom:0.8rem">来源用纸档已作废，本签内容只读留存</p>

      <div class="result-board">
        <div class="figure">{{ lab.paper_m2 ?? '—' }}<span>m² 用纸</span></div>
        <p class="stat-line">{{ lab.box_name || '盒已缺失' }} · 丝带约 {{ lab.ribbon_m ?? '—' }} m</p>
      </div>

      <dl class="label-meta">
        <dt>盒名</dt><dd>{{ lab.box_name || '盒已缺失' }}</dd>
        <dt>用纸 paper_m2</dt><dd>{{ lab.paper_m2 ?? '—' }} m²</dd>
        <dt>丝带 ribbon_m</dt><dd>{{ lab.ribbon_m ?? '—' }} m</dd>
        <dt>绕法</dt><dd>{{ lab.wrap_style ?? '—' }}</dd>
        <dt>折边系数</dt><dd>{{ lab.overlap ?? '—' }}</dd>
        <dt>出签时间</dt><dd>{{ lab.issued_at }}</dd>
        <dt v-if="lab.printed_at">打印时间</dt><dd v-if="lab.printed_at">{{ lab.printed_at }}</dd>
        <dt>内容校验和</dt>
        <dd>SHA-256<code class="checksum">{{ lab.checksum }}</code></dd>
      </dl>

      <div class="row" style="margin-top:1.25rem">
        <button v-if="lab.status === 'queued'" class="ribbon" :disabled="busy" @click="markPrinted">标记已打印</button>
        <router-link class="btn ghost" :to="`/runs/${lab.run_id}`">回到用纸档 #{{ lab.run_id }}</router-link>
        <router-link class="btn ghost" to="/labels">返回队列</router-link>
      </div>
    </template>
  </div>
</template>
