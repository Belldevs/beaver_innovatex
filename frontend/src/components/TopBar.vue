<template>
  <header class="bar">
    <div class="brand">
      <span class="mark" aria-hidden="true">B</span>
      <span class="name">Beaver</span>
    </div>
    <div class="spacer"></div>

    <label class="field">
      <span class="sr">Signed in as</span>
      <select :value="state.userId" @change="selectUser($event.target.value)">
        <option v-for="u in state.users" :key="u.id" :value="u.id">{{ u.name }}, {{ u.title }}</option>
      </select>
    </label>

    <div v-if="user" class="roles" role="group" aria-label="Active role">
      <button v-for="r in user.roles" :key="r" :aria-pressed="r === state.role" @click="setRole(r)">{{ r }}</button>
    </div>

    <span class="status" :class="status.tone" :title="status.hint">
      <i aria-hidden="true"></i>{{ status.text }}
    </span>

    <button class="icon narrow" @click="state.showHistory = !state.showHistory" aria-label="Toggle saved conversations">History</button>
    <button v-if="user" class="avatar" @click="state.showProfile = true" :aria-label="`Open profile for ${user.name}`">{{ initials }}</button>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { state, user, selectUser, setRole } from '../store'

const initials = computed(() => (user.value?.name || '').split(' ').map(w => w[0]).join('').slice(0, 2))
const status = computed(() => {
  const h = state.health
  if (!state.backendUp) return { tone: 'warn', text: 'Backend offline', hint: 'Start the FastAPI server on port 5000.' }
  if (h?.online && h.model_ready) return { tone: 'ok', text: `Ollama: ${h.model}`, hint: 'Questions are understood by the local model. Nothing leaves this machine.' }
  if (h?.online) return { tone: 'warn', text: 'Model not pulled', hint: `Run: ollama pull ${h.model}. Until then Beaver uses its built-in rule-based parser.` }
  return { tone: 'warn', text: 'Ollama off: rule-based mode', hint: 'Start Ollama for natural-language understanding. Calculations and access rules work either way.' }
})
</script>

<style scoped>
.bar { display: flex; align-items: center; gap: 12px; padding: 10px 18px; border-bottom: 1px solid var(--line); background: var(--surface); flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 9px; }
.mark { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; background: var(--accent); color: var(--accent-ink); font-weight: 700; }
.name { font-weight: 700; font-size: 17px; letter-spacing: -0.01em; }
.spacer { flex: 1; }
select { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; max-width: 230px; }
.roles { display: inline-flex; border: 1px solid var(--line); border-radius: 9px; overflow: hidden; }
.roles button { background: transparent; border: 0; padding: 6px 13px; cursor: pointer; color: var(--muted); }
.roles button + button { border-left: 1px solid var(--line); }
.roles button[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); font-weight: 600; }
.status { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; color: var(--muted); }
.status i { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
.status.ok i { background: #2fa36b; }
.status.warn { color: var(--warn-ink); }
.status.warn i { background: #d9962b; }
.avatar { width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--line); background: var(--accent-soft); color: var(--ink); font-weight: 600; cursor: pointer; }
.icon { background: transparent; border: 1px solid var(--line); border-radius: 8px; padding: 5px 10px; cursor: pointer; }
.narrow { display: none; }
@media (max-width: 860px) { .narrow { display: inline-block; } .status { order: 9; width: 100%; } }
</style>
