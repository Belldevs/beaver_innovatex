<template>
  <div class="chat">
    <div ref="scroller" class="scroll">
      <div class="col">
        <div v-if="!current || !current.messages.length" class="empty">
          <h1>What would you like to know?</h1>
          <p>You're asking as <strong>{{ state.role }}</strong>. Beaver answers only from data this role is cleared to read, and every figure is calculated from the dataset.</p>
          <div class="chips">
            <button v-for="s in state.suggestions" :key="s" @click="send(s)">{{ s }}</button>
          </div>
        </div>
        <MessageBubble v-for="(m, i) in current?.messages || []" :key="i" :message="m" />
        <div v-if="state.busy" class="thinking" role="status"><span class="avatar" aria-hidden="true">B</span><span>Working it out</span><i></i><i></i><i></i></div>
      </div>
    </div>

    <form class="composer" @submit.prevent="submit">
      <div class="col">
        <div class="box">
          <label class="sr" for="q">Ask a question</label>
          <textarea id="q" ref="box" v-model="draft" rows="1" placeholder="Ask about revenue, loans, transactions, risk…"
                    @keydown="onKey" @input="resize"></textarea>
          <button class="btn" :disabled="state.busy || !draft.trim()">Send</button>
        </div>
        <p class="fine">Enter to send, Shift+Enter for a new line.</p>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { state, current, send } from '../store'
import MessageBubble from './MessageBubble.vue'

const draft = ref('')
const scroller = ref(null)
const box = ref(null)

watch(() => [current.value?.messages.length, state.busy, state.currentId], async () => {
  await nextTick()
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight })
})

function resize() {
  const el = box.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}
function submit() {
  const t = draft.value
  if (!t.trim()) return
  draft.value = ''
  nextTick(resize)
  send(t)
}
function onKey(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit() }
}
</script>

<style scoped>
.chat { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.scroll { flex: 1; overflow-y: auto; }
.col { max-width: 760px; margin: 0 auto; padding: 0 20px; }
.empty { padding: 11vh 0 20px; }
.empty h1 { font-size: 28px; letter-spacing: -0.02em; margin: 0 0 8px; }
.empty p { color: var(--muted); max-width: 56ch; margin: 0 0 22px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chips button { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 8px 12px; cursor: pointer; text-align: left; }
.chips button:hover { border-color: var(--accent); }
.thinking { display: flex; align-items: center; gap: 10px; color: var(--muted); padding: 14px 0 24px; }
.avatar { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; background: var(--accent); color: var(--accent-ink); font-weight: 700; font-size: 13px; }
.thinking i { width: 5px; height: 5px; border-radius: 50%; background: var(--muted); animation: blink 1.2s infinite; }
.thinking i:nth-of-type(2) { animation-delay: .15s; } .thinking i:nth-of-type(3) { animation-delay: .3s; }
@keyframes blink { 0%, 80%, 100% { opacity: .25; } 40% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .thinking i { animation: none; opacity: .6; } }
.composer { padding: 10px 0 14px; background: linear-gradient(to top, var(--bg) 70%, transparent); }
.box { display: flex; align-items: flex-end; gap: 10px; background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 8px 8px 8px 14px; }
.box:focus-within { border-color: var(--accent); }
textarea { flex: 1; resize: none; border: 0; background: transparent; outline: none; padding: 6px 0; max-height: 180px; }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.fine { margin: 6px 4px 0; font-size: 12px; color: var(--muted); }
</style>
