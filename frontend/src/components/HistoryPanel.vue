<template>
  <aside class="history" :class="{ open: state.showHistory }" aria-label="Saved conversations">
    <div class="head">
      <h2>Conversations</h2>
      <button class="btn" @click="newChat">New chat</button>
    </div>
    <p class="note">Saved in this browser for 7 days. Only chats asked as <strong>{{ state.role }}</strong> are listed.</p>

    <ul v-if="visibleChats.length">
      <li v-for="c in visibleChats" :key="c.id" :class="{ active: c.id === state.currentId }">
        <button class="open" @click="openChat(c.id)">
          <span class="title">{{ c.title }}</span>
          <span class="when">{{ ago(c.updated) }}</span>
        </button>
        <button class="del" @click="deleteChat(c.id)" :aria-label="`Delete conversation: ${c.title}`">
          <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3z"/></svg>
        </button>
      </li>
    </ul>
    <p v-else class="none">No saved conversations yet. Ask a question and it will appear here.</p>

    <button v-if="state.chats.length" class="clear" @click="clearChats">Clear all saved conversations</button>
  </aside>
</template>

<script setup>
import { state, visibleChats, newChat, openChat, deleteChat, clearChats } from '../store'

function ago(ts) {
  const s = (Date.now() - ts) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}
</script>

<style scoped>
.history { background: var(--surface); border-left: 1px solid var(--line); padding: 16px 12px; display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }
.head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
h2 { font-size: 15px; margin: 0; }
.note, .none { font-size: 12.5px; color: var(--muted); margin: 8px 2px 12px; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
li { display: flex; align-items: center; border-radius: 9px; }
li:hover, li.active { background: var(--accent-soft); }
.open { flex: 1; min-width: 0; background: none; border: 0; text-align: left; padding: 8px 8px; cursor: pointer; display: flex; flex-direction: column; }
.title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.when { font-size: 12px; color: var(--muted); }
.del { background: none; border: 0; padding: 8px; cursor: pointer; color: var(--muted); border-radius: 8px; }
.del:hover { color: var(--neg); }
.clear { margin-top: auto; background: none; border: 0; color: var(--muted); cursor: pointer; padding: 10px 4px 2px; text-align: left; font-size: 13px; }
.clear:hover { color: var(--neg); }
@media (max-width: 860px) {
  .history { position: fixed; top: 0; right: 0; bottom: 0; width: min(320px, 88vw); transform: translateX(100%); transition: transform .2s; z-index: 20; box-shadow: -8px 0 24px rgba(0, 0, 0, .15); }
  .history.open { transform: none; }
}
@media (prefers-reduced-motion: reduce) { .history { transition: none; } }
</style>
