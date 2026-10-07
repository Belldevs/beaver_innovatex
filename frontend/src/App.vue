<template>
  <div class="app">
    <section class="main">
      <TopBar />
      <div v-if="!state.backendUp && !state.users.length" class="down">
        <h2>Can't reach the Beaver backend</h2>
        <p>Start it from the <code>analytics</code> folder, then retry:</p>
        <pre>uvicorn main:app --port 5000</pre>
        <button class="btn" @click="init">Retry</button>
      </div>
      <ChatWindow v-else-if="user" />
    </section>
    <HistoryPanel />
    <ProfilePanel />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { state, user, init } from './store'
import TopBar from './components/TopBar.vue'
import ChatWindow from './components/ChatWindow.vue'
import HistoryPanel from './components/HistoryPanel.vue'
import ProfilePanel from './components/ProfilePanel.vue'

onMounted(init)
</script>

<style>
:root {
  --bg: #f3f5f4; --surface: #ffffff; --ink: #15211e; --muted: #5c6a66; --line: #dce3e0;
  --accent: #0d6b5b; --accent-ink: #ffffff; --accent-soft: #e1f0ec;
  --warn-bg: #fff3d6; --warn-ink: #7a4b00; --neg: #b3412d;
  --font: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1715; --surface: #16211e; --ink: #e6eeeb; --muted: #9aaba6; --line: #263632;
    --accent: #3fb8a0; --accent-ink: #08130f; --accent-soft: #153029;
    --warn-bg: #3a2d10; --warn-ink: #f1c77a; --neg: #e8806c;
  }
}
* { box-sizing: border-box; }
html, body, #app { height: 100%; margin: 0; }
body { font-family: var(--font); background: var(--bg); color: var(--ink); font-size: 15px; line-height: 1.55; }
button, select, textarea { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.btn { background: var(--accent); color: var(--accent-ink); border: 0; border-radius: 8px; padding: 8px 14px; cursor: pointer; font-weight: 600; }
.btn.ghost { background: transparent; color: var(--ink); border: 1px solid var(--line); font-weight: 500; }

.app { display: grid; grid-template-columns: minmax(0, 1fr) 300px; height: 100dvh; }
.main { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.down { margin: 12vh auto; max-width: 440px; padding: 0 20px; }
.down pre { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; overflow-x: auto; }
@media (max-width: 860px) { .app { grid-template-columns: minmax(0, 1fr); } }
</style>
