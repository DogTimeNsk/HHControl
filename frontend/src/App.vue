<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from './services/api'

type Resume = { id:number; title:string; hh_resume_id:string; enabled:boolean; status:string|null; published_at:string|null; next_publish_at:string|null; publish_available:boolean|null; last_error:string|null }
const loggedIn = ref(false), username = ref('admin'), password = ref(''), resumes = ref<Resume[]>([]), connected = ref(false), message = ref(''), busy = ref(false), history = ref<string[]>([]), manualOpen = ref(false), helpOpen = ref(false), manualId = ref(''), browserSaved = ref(false)
const fmt = (v:string|null) => v ? new Date(v).toLocaleString('ru-RU') : '—'
async function load() { resumes.value = await api.get<Resume[]>('/resumes'); connected.value = (await api.get<{connected:boolean}>('/connection')).connected; browserSaved.value = (await api.get<{saved:boolean}>('/browser/session')).saved }
async function login() { try { await api.post('/auth/login', { username:username.value, password:password.value }); loggedIn.value=true; password.value=''; await load() } catch(e) { message.value=(e as Error).message } }
async function connect() { const r = await api.get<{authorization_url:string}>('/oauth/connect'); window.open(r.authorization_url, '_blank', 'width=600,height=700'); message.value='Завершите вход в открывшемся окне, затем синхронизируйте резюме.' }
async function disconnect() { if (!confirm('Отключить HH-аккаунт? Локально сохранённые токены будут удалены, резюме на hh.ru не изменятся.')) return; await action(async()=> { await api.delete('/connection'); connected.value=false; message.value='HH-аккаунт отключён. Теперь можно подключить другой.' }) }
async function addManual() { await action(async()=> { const resume = await api.post<Resume>('/resumes/manual', { hh_resume_id: manualId.value }); const index=resumes.value.findIndex(x=>x.id===resume.id); if (index >= 0) resumes.value[index]=resume; else resumes.value.push(resume); manualId.value=''; manualOpen.value=false; message.value='Резюме подключено. Автообновление выключено.' }) }
async function saveBrowser() { await action(async()=> { await api.post('/browser/session/save'); browserSaved.value=true; message.value='Browser session сохранена. Теперь синхронизация использует личный кабинет HH.' }) }
async function openBrowser() { await action(async()=> { await api.post('/browser/open'); window.open('/browser/vnc.html?autoconnect=true&path=browser/websockify', '_blank') }) }
function openVnc() { window.open('/browser/vnc.html?autoconnect=true&path=browser/websockify', '_blank', 'noopener') }
async function sync() { await action(async()=> { resumes.value = await api.post<Resume[]>('/resumes/sync'); message.value='Список резюме синхронизирован.' }) }
async function toggle(r:Resume) { await action(async()=> { const updated=await api.patch<Resume>(`/resumes/${r.id}`, {enabled:!r.enabled}); Object.assign(r,updated) }) }
async function publish(r:Resume) { if (!confirm(`Обновить «${r.title}» сейчас?`)) return; await action(async()=> { const e=await api.post<{message:string}>(`/resumes/${r.id}/publish`); message.value=e.message; await load() }) }
async function remove(r:Resume) { if (!confirm(`Убрать «${r.title}» из локального управления? На hh.ru оно останется.`)) return; await action(async()=> { await api.delete(`/resumes/${r.id}`); resumes.value=resumes.value.filter(x=>x.id!==r.id) }) }
async function showHistory(r:Resume) { await action(async()=> { const rows=await api.get<{started_at:string,result:string,message:string}[]>(`/resumes/${r.id}/history`); history.value=rows.map(x=>`${new Date(x.started_at).toLocaleString('ru-RU')} — ${x.result}: ${x.message}`) }) }
async function action(fn:()=>Promise<void>) { try { busy.value=true; await fn() } catch(e) { message.value=(e as Error).message } finally { busy.value=false } }
async function logout() { await api.post('/auth/logout'); loggedIn.value=false }
onMounted(async()=> { try { await api.get('/auth/me'); loggedIn.value=true; await load() } catch {} })
</script>

<template>
  <main class="shell">
    <section v-if="!loggedIn" class="card login"><h1>HH Control</h1><p>Вход администратора</p><input v-model="username" autocomplete="username" placeholder="Имя" /><input v-model="password" type="password" autocomplete="current-password" placeholder="Пароль" @keyup.enter="login" /><button @click="login">Войти</button><p class="message">{{ message }}</p></section>
    <template v-else>
      <header>
        <div class="brand"><h1>HH Control</h1><small>Browser: {{ browserSaved ? 'сессия сохранена' : 'требуется вход' }}</small></div>
        <div class="actions">
          <button class="secondary" @click="helpOpen=true">Как это работает</button>
          <button :disabled="busy" @click="openBrowser">Войти в hh.ru</button>
          <button class="secondary" @click="openVnc">Открыть VNC</button>
          <button :disabled="busy" @click="saveBrowser">Сохранить сессию</button>
          <button :disabled="busy || !browserSaved" @click="manualOpen=true">Добавить резюме</button>
          <button :disabled="busy || !browserSaved" @click="sync">Синхронизировать</button>
          <button class="secondary" @click="logout">Выйти</button>
        </div>
      </header>
      <p v-if="message" class="message">{{ message }}</p>
      <section class="card resume-list"><div v-if="!resumes.length" class="empty">{{ connected ? 'Резюме ещё не синхронизированы.' : 'Подключите аккаунт hh.ru.' }}</div><article v-for="r in resumes" :key="r.id" class="resume"><div class="resume-title"><h2>{{ r.title }}</h2><small>ID: {{ r.hh_resume_id }} · {{ r.status || 'статус неизвестен' }}</small></div><dl><div><dt>Обновлено</dt><dd>{{ fmt(r.published_at) }}</dd></div><div><dt>Поднятие</dt><dd>{{ r.publish_available === true ? 'доступно' : r.publish_available === false ? 'пока недоступно' : 'ещё не проверено' }}</dd></div><div><dt>Следующая публикация</dt><dd>{{ fmt(r.next_publish_at) }}</dd></div><div v-if="r.last_error"><dt>Ошибка</dt><dd class="error">{{ r.last_error }}</dd></div></dl><div class="resume-actions"><label><input :checked="r.enabled" type="checkbox" @change="toggle(r)" /> Автообновление</label><button :disabled="busy" @click="publish(r)">Обновить сейчас</button><button class="secondary" @click="showHistory(r)">История</button><button class="secondary" @click="remove(r)">Убрать</button></div></article></section>
      <section v-if="history.length" class="card history"><div class="section-heading"><h2>История операций</h2><button class="icon-button secondary" aria-label="Закрыть историю" @click="history=[]">×</button></div><p v-for="row in history" :key="row">{{ row }}</p></section>
      <div v-if="manualOpen" class="modal-backdrop" @click.self="manualOpen=false"><form class="modal card" @submit.prevent="addManual"><h2>Добавить резюме вручную</h2><p>Скопируйте ID из адреса страницы резюме на hh.ru.</p><input v-model.trim="manualId" required maxlength="128" pattern="[A-Za-z0-9]+" placeholder="ID резюме" autofocus /><div class="actions"><button :disabled="busy">Подключить</button><button type="button" class="secondary" @click="manualOpen=false">Отмена</button></div></form></div>
      <div v-if="helpOpen" class="modal-backdrop" @click.self="helpOpen=false"><section class="modal card help" role="dialog" aria-modal="true" aria-labelledby="help-title"><div class="section-heading"><h2 id="help-title">О HH Control</h2><button class="icon-button secondary" aria-label="Закрыть справку" @click="helpOpen=false">×</button></div><p>HH Control помогает отслеживать доступность и автоматически поднимать ваши собственные резюме в поиске HeadHunter.</p><p>Сначала войдите в hh.ru через VNC и сохраните сессию. Затем добавьте и синхронизируйте резюме, включите автообновление для нужных из них.</p><p>«Открыть VNC» показывает текущий экран браузера без создания новой сессии. Никому не передавайте доступ к этой странице.</p><div class="actions"><button @click="helpOpen=false">Понятно</button></div></section></div>
    </template>
  </main>
</template>
