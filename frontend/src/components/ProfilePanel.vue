<template>
  <dialog ref="dlg" @close="state.showProfile = false" @click.self="state.showProfile = false">
    <div v-if="user" class="card">
      <header>
        <div>
          <h2>{{ user.name }}</h2>
          <p class="sub">{{ user.title }}</p>
        </div>
        <button class="x" @click="state.showProfile = false" aria-label="Close profile">Close</button>
      </header>

      <section>
        <h3>Your roles</h3>
        <ul class="roles">
          <li v-for="r in user.roles" :key="r">
            <strong>{{ r }}</strong><span v-if="r === state.role" class="now">active</span>
            <p>{{ state.roles[r]?.description }}</p>
            <p class="tags"><span v-for="t in state.roles[r]?.allowed_tags" :key="t">{{ t === '*' ? 'all data' : t }}</span></p>
          </li>
        </ul>
        <p class="hint">Switch roles from the bar at the top. Each role sees only the data its tags allow.</p>
      </section>

      <section v-if="isAdminRole">
        <h3>Manage who holds which role</h3>
        <div v-for="u in state.users" :key="u.id" class="row">
          <div class="who"><strong>{{ u.name }}</strong><span>{{ u.title }}</span></div>
          <label v-for="(def, name) in state.roles" :key="name" class="chk">
            <input type="checkbox" :checked="(edits[u.id] || []).includes(name)" @change="toggle(u.id, name)" />{{ name }}
          </label>
          <button class="btn" :disabled="!dirty(u) || !(edits[u.id] || []).length" @click="save(u)">Save</button>
        </div>
        <p v-if="msg" class="hint">{{ msg }}</p>
      </section>
      <section v-else>
        <p class="hint">Switch to an admin role to manage who holds which role.</p>
      </section>
    </div>
  </dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { state, user, isAdminRole, saveUserRoles } from '../store'

const dlg = ref(null)
const edits = reactive({})
const msg = ref('')

watch(() => state.showProfile, (open) => {
  if (open) {
    state.users.forEach(u => { edits[u.id] = [...u.roles] })
    msg.value = ''
    if (!dlg.value.open) dlg.value.showModal()
  } else if (dlg.value?.open) dlg.value.close()
})

const toggle = (id, role) => {
  const s = new Set(edits[id] || [])
  s.has(role) ? s.delete(role) : s.add(role)
  edits[id] = [...s]
}
const dirty = (u) => [...(edits[u.id] || [])].sort().join() !== [...u.roles].sort().join()

async function save(u) {
  try { await saveUserRoles(u.id, edits[u.id]); msg.value = `Saved roles for ${u.name}.` }
  catch (e) { msg.value = e.message }
}
</script>

<style scoped>
dialog { border: 1px solid var(--line); border-radius: 14px; padding: 0; width: min(640px, 94vw); background: var(--surface); color: var(--ink); }
dialog::backdrop { background: rgba(0, 0, 0, .4); }
.card { padding: 20px 22px 22px; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
h2 { margin: 0; font-size: 20px; } h3 { font-size: 14px; margin: 22px 0 8px; }
.sub { margin: 0; color: var(--muted); }
.x { background: none; border: 1px solid var(--line); border-radius: 8px; padding: 5px 10px; cursor: pointer; }
.roles { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.roles li { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
.roles p { margin: 3px 0 0; font-size: 13.5px; color: var(--muted); }
.now { margin-left: 8px; font-size: 12px; background: var(--accent-soft); border-radius: 6px; padding: 1px 7px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; }
.tags span { border: 1px solid var(--line); border-radius: 6px; padding: 0 7px; font-size: 12.5px; }
.row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 14px; padding: 9px 0; border-top: 1px solid var(--line); }
.who { display: flex; flex-direction: column; min-width: 150px; flex: 1; } .who span { font-size: 12.5px; color: var(--muted); }
.chk { display: inline-flex; align-items: center; gap: 5px; font-size: 14px; }
.btn:disabled { opacity: .4; cursor: not-allowed; }
.hint { font-size: 13px; color: var(--muted); margin: 10px 0 0; }
</style>
