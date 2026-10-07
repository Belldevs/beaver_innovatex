<template>
  <div v-if="message.from === 'user'" class="user"><p>{{ message.text }}</p></div>

  <div v-else class="beaver">
    <span class="avatar" aria-hidden="true">B</span>
    <div class="body">
      <div v-if="message.kind === 'denied'" class="notice">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5Zm-3 8V7a3 3 0 1 1 6 0v3H9Z"/></svg>
        <div>
          <p class="text">{{ message.answer }}</p>
          <p class="tags"><span v-for="t in tags" :key="t" class="tag">{{ t }}</span></p>
        </div>
      </div>
      <p v-else class="text" :class="{ err: message.kind === 'error' }">{{ message.answer }}</p>

      <BarChart v-if="message.chart" :chart="message.chart" />

      <div v-if="message.table && message.table.rows.length > 1" class="tablewrap">
        <table>
          <thead><tr><th v-for="c in message.table.columns" :key="c">{{ c }}</th></tr></thead>
          <tbody><tr v-for="(row, i) in message.table.rows" :key="i"><td v-for="(cell, j) in row" :key="j">{{ cell }}</td></tr></tbody>
        </table>
      </div>

      <div v-if="message.suggestions?.length" class="chips">
        <button v-for="s in message.suggestions" :key="s" @click="send(s)">{{ s }}</button>
      </div>

      <p v-if="message.kind === 'answer'" class="meta">Answered as {{ message.role }}, understood by {{ planner }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { send } from '../store'
import BarChart from './BarChart.vue'

const props = defineProps({ message: { type: Object, required: true } })
const tags = computed(() => [...new Set((props.message.denied || []).flatMap(d => d.missing))])
const planner = computed(() => (props.message.planner || '').startsWith('ollama') ? 'Ollama' : 'the built-in rule parser')
</script>

<style scoped>
.user { display: flex; justify-content: flex-end; padding: 18px 0 6px; }
.user p { margin: 0; max-width: 85%; background: var(--accent-soft); border-radius: 14px 14px 4px 14px; padding: 9px 14px; white-space: pre-wrap; }
.beaver { display: flex; gap: 12px; padding: 14px 0 20px; }
.avatar { flex: none; display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; background: var(--accent); color: var(--accent-ink); font-weight: 700; font-size: 13px; margin-top: 2px; }
.body { min-width: 0; flex: 1; }
.text { margin: 0 0 8px; white-space: pre-wrap; max-width: 68ch; }
.text.err { color: var(--neg); }
.notice { display: flex; gap: 10px; background: var(--warn-bg); color: var(--warn-ink); border-radius: 10px; padding: 11px 14px; }
.notice svg { flex: none; margin-top: 3px; }
.notice .text { margin: 0; }
.tags { margin: 8px 0 0; display: flex; gap: 6px; flex-wrap: wrap; }
.tag { border: 1px solid currentColor; border-radius: 6px; padding: 0 7px; font-size: 12.5px; }
.tablewrap { overflow-x: auto; margin: 10px 0; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { padding: 8px 12px; text-align: left; white-space: nowrap; }
th { color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--line); }
tr + tr td { border-top: 1px solid var(--line); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.chips button { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 7px 11px; cursor: pointer; text-align: left; }
.chips button:hover { border-color: var(--accent); }
.meta { margin: 8px 0 0; font-size: 12px; color: var(--muted); }
</style>
