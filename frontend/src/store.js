import { reactive, computed } from 'vue'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const MAX_CHATS = 20                     // saved conversations per user
const TTL_MS = 7 * 24 * 3600 * 1000      // "temporary": dropped after 7 days

export const state = reactive({
  users: [], roles: {}, userId: null, role: null,
  chats: [], currentId: null,
  suggestions: [], health: null, backendUp: true,
  busy: false, showProfile: false, showHistory: false,
})

export const user = computed(() => state.users.find(u => u.id === state.userId) || null)
export const current = computed(() => state.chats.find(c => c.id === state.currentId) || null)
// Chats are only listed under the role they were asked in, so toggling roles never exposes another role's answers.
export const visibleChats = computed(() =>
  state.chats.filter(c => c.role === state.role).sort((a, b) => b.updated - a.updated))
export const isAdminRole = computed(() => !!state.roles[state.role]?.allowed_tags?.includes('*'))

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`)
  return data
}

// ── local storage (per user) ──
const chatKey = () => `beaver:chats:${state.userId}`
function loadChats() {
  try {
    const raw = JSON.parse(localStorage.getItem(chatKey()) || '[]')
    state.chats = raw.filter(c => Date.now() - c.updated < TTL_MS)
  } catch { state.chats = [] }
}
function saveChats() {
  state.chats = [...state.chats].sort((a, b) => b.updated - a.updated).slice(0, MAX_CHATS)
  try { localStorage.setItem(chatKey(), JSON.stringify(state.chats)) } catch { /* storage full or blocked */ }
}

// ── lifecycle ──
export async function refreshHealth() {
  try { state.health = (await api('/api/health')).ollama; state.backendUp = true }
  catch { state.backendUp = false; state.health = null }
}

async function loadSuggestions() {
  try { state.suggestions = (await api(`/api/suggestions?user_id=${state.userId}&role=${state.role}`)).suggestions }
  catch { state.suggestions = [] }
}

export async function init() {
  await refreshHealth()
  if (!state.backendUp) return
  const [users, roles] = await Promise.all([api('/api/users'), api('/api/roles')])
  state.users = users; state.roles = roles
  const last = localStorage.getItem('beaver:lastUser')
  selectUser(users.some(u => u.id === last) ? last : users[0].id)
  setInterval(refreshHealth, 20000)
}

export function selectUser(id) {
  state.userId = id
  localStorage.setItem('beaver:lastUser', id)
  state.role = user.value.roles[0]
  state.currentId = null
  loadChats(); loadSuggestions()
}

export function setRole(role) {
  if (role === state.role) return
  state.role = role
  state.currentId = null        // a role switch starts a fresh conversation
  loadSuggestions()
}

export const newChat = () => { state.currentId = null; state.showHistory = false }
export const openChat = (id) => { state.currentId = id; state.showHistory = false }
export function deleteChat(id) {
  state.chats = state.chats.filter(c => c.id !== id)
  if (state.currentId === id) state.currentId = null
  saveChats()
}
export function clearChats() { state.chats = []; state.currentId = null; saveChats() }

export async function send(text) {
  text = text.trim()
  if (!text || state.busy) return
  let chat = current.value
  if (!chat) {
    chat = { id: crypto.randomUUID(), role: state.role, title: text.slice(0, 48), created: Date.now(), updated: Date.now(), messages: [] }
    state.chats.unshift(chat)
    state.currentId = chat.id
    chat = current.value
  }
  chat.messages.push({ from: 'user', text, ts: Date.now() })
  state.busy = true
  try {
    const r = await api('/api/chat', { method: 'POST', body: { user_id: state.userId, role: state.role, message: text } })
    chat.messages.push({ from: 'beaver', ts: Date.now(), ...r })
  } catch (e) {
    chat.messages.push({ from: 'beaver', kind: 'error', ts: Date.now(),
      answer: state.backendUp ? e.message : 'Cannot reach the Beaver backend. Start it with: uvicorn main:app --port 5000' })
    refreshHealth()
  } finally {
    chat.updated = Date.now()
    state.busy = false
    saveChats()
  }
}

// ── profile / role management (admin only, enforced again on the server) ──
export async function saveUserRoles(targetId, roles) {
  await api(`/api/users/${targetId}/roles`, { method: 'PUT', body: { actor_id: state.userId, actor_role: state.role, roles } })
  state.users = await api('/api/users')
  if (!user.value.roles.includes(state.role)) setRole(user.value.roles[0])
}
