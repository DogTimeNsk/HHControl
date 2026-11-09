<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ browserSaved: boolean; busy: boolean; setupReady: boolean }>()
const emit = defineEmits<{
  help: []
  loginHh: []
  openVnc: []
  saveBrowser: []
  addResume: []
  syncResumes: []
  findTelegramChats: []
  logout: []
}>()
const browserOpen = ref(false)
const resumeOpen = ref(false)
function toggle(menu: 'browser' | 'resume') {
  if (menu === 'browser') {
    browserOpen.value = !browserOpen.value
    resumeOpen.value = false
  } else {
    resumeOpen.value = !resumeOpen.value
    browserOpen.value = false
  }
}
function emitAndClose(event: 'loginHh' | 'openVnc' | 'saveBrowser' | 'addResume' | 'syncResumes') {
  browserOpen.value = false
  resumeOpen.value = false
  if (event === 'loginHh') emit('loginHh')
  if (event === 'openVnc') emit('openVnc')
  if (event === 'saveBrowser') emit('saveBrowser')
  if (event === 'addResume') emit('addResume')
  if (event === 'syncResumes') emit('syncResumes')
}
</script>

<template>
  <header>
    <div class="brand"><h1>HH Control</h1><small>Browser: {{ browserSaved ? 'сессия сохранена' : 'требуется вход' }}</small></div>
    <div class="action-panel">
      <button class="secondary" @click="emit('help')">Справка</button>
      <button class="secondary" :disabled="busy" @click="emit('findTelegramChats')">Найти Telegram chat_id</button>
      <div class="menu-dropdown">
        <button class="secondary" :aria-expanded="browserOpen" @click="toggle('browser')">hh.ru <span aria-hidden="true">▾</span></button>
        <div v-if="browserOpen" class="dropdown-menu">
          <button :disabled="busy" @click="emitAndClose('loginHh')">Войти в hh.ru</button>
          <button class="secondary" @click="emitAndClose('openVnc')">Открыть VNC</button>
          <button :disabled="busy || !setupReady" @click="emitAndClose('saveBrowser')">Сохранить сессию</button>
        </div>
      </div>
      <div class="menu-dropdown">
        <button class="secondary" :aria-expanded="resumeOpen" @click="toggle('resume')">Резюме <span aria-hidden="true">▾</span></button>
        <div v-if="resumeOpen" class="dropdown-menu">
          <button :disabled="busy || !browserSaved || !setupReady" @click="emitAndClose('addResume')">Добавить резюме</button>
          <button :disabled="busy || !browserSaved || !setupReady" @click="emitAndClose('syncResumes')">Синхронизировать</button>
        </div>
      </div>
      <button class="secondary" @click="emit('logout')">Выйти</button>
    </div>
  </header>
</template>

