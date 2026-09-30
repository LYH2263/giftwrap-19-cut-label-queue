<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getJSON, postJSON } from '../api'

const props = defineProps({ id: String })
const router = useRouter()
const run = ref(null)
const labels = ref([])
const err = ref('')
const busy = ref(false)
const confirming = ref(false)

const ribbonM = (r) => {
  const rb = r?.result?.ribbon
  return rb == null ? null : (rb.ribbon_m ?? rb)
}

async function load() {
  err.value = ''
  try {
    run.value = await getJSON(`/api/runs/${props.id}`)
    labels.value = (await getJSON(`/api/labels?run_id=${props.id}`)).items
  } catch (e) {
    err.value = String(e.message || e)
  }
}

onMounted(load)

async function issue() {
  err.value = ''
  busy.value = true
  try {
    const lab = await postJSON(`/api/runs/${props.id}/labels`, {})
    await router.push(`/labels/${lab.id}`)
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

async function voidRun() {
  err.value = ''
  busy.value = true
  try {
    await postJSON(`/api/runs/${props.id}/void`, {})
    confirming.value = false
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
    <template v-else-if="run">
      <h1>
        用纸档 #{{ run.id }}
        <span class="pill" :class="{ warn: run.voided }" style="margin-left:0.6rem">
          {{ run.voided ? '已作废' : '在用' }}
        </span>
      </h1>
      <p class="lede">{{ run.box_name || '盒已缺失' }}</p>
      <dl class="label-meta">
        <dt>用纸 paper_m2</dt><dd>{{ run.result?.paper_m2 ?? '—' }} m²</dd>
        <dt>丝带 ribbon_m</dt><dd>{{ ribbonM(run) ?? '—' }} m</dd>
        <dt>绕法</dt><dd>{{ run.result?.ribbon?.wrap_style ?? '—' }}</dd>
        <dt>折边系数</dt><dd>{{ run.overlap ?? '—' }}</dd>
        <dt>落库时间</dt><dd>{{ run.created_at }}</dd>
        <dt v-if="run.note">备注</dt><dd v-if="run.note">{{ run.note }}</dd>
      </dl>

      <div class="row" style="margin-top:1.25rem">
        <template v-if="!run.voided">
          <button class="ribbon" :disabled="busy" @click="issue">出签</button>
          <template v-if="confirming">
            <button class="ghost" :disabled="busy" @click="voidRun">确认作废</button>
            <button class="ghost" :disabled="busy" @click="confirming = false">取消</button>
          </template>
          <button v-else class="ghost" :disabled="busy" @click="confirming = true">作废此用纸档</button>
        </template>
        <router-link class="btn ghost" to="/history">返回用纸档列表</router-link>
      </div>

      <h2 style="margin-top:2rem;font-size:1.15rem">该用纸档的裁切签</h2>
      <p v-if="!labels.length" class="empty">还没有出过签。</p>
      <ul v-else class="item-list">
        <li v-for="l in labels" :key="l.id">
          <router-link :to="`/labels/${l.id}`">签 #{{ l.id }}</router-link>
          <span class="meta">
            {{ l.paper_m2 }} m² · {{ l.ribbon_m ?? '—' }} m
            <span class="pill" :class="{ done: l.status === 'printed' }" style="margin-left:0.6rem">
              {{ l.status === 'printed' ? '已打印' : '待打印' }}
            </span>
          </span>
        </li>
      </ul>
    </template>
  </div>
</template>
