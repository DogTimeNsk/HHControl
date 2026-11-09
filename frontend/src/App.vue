<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppHeader from './components/AppHeader.vue'
import HelpModal from './components/HelpModal.vue'
import ManualResumeModal from './components/ManualResumeModal.vue'
import OperationHistory from './components/OperationHistory.vue'
import ResumeList from './components/ResumeList.vue'
import SetupAlert from './components/SetupAlert.vue'
import VacancyStatistics from './components/VacancyStatistics.vue'
import { useDashboard } from './composables/useDashboard'

const dashboard = useDashboard()
const manualOpen = ref(false)
const helpOpen = ref(false)

async function addManualResume(id: string) {
  await dashboard.addManualResume(id)
  manualOpen.value = false
}

onMounted(async () => {
  try {
    await dashboard.load()
    dashboard.loggedIn = true
  } catch {
    // Anonymous users see the login screen.
  }
})
</script>

<template>
  <main class="shell">
    <section v-if="!dashboard.loggedIn" class="card login">
      <h1>HH Control</h1><p>Вход администратора</p>
      <input v-model="dashboard.username" autocomplete="username" placeholder="Имя" />
      <input v-model="dashboard.password" type="password" autocomplete="current-password" placeholder="Пароль" @keyup.enter="dashboard.login" />
      <button @click="dashboard.login">Войти</button><p class="message">{{ dashboard.message }}</p>
    </section>

    <template v-else>
      <AppHeader :browser-saved="dashboard.browserSaved" :busy="dashboard.busy" :setup-ready="dashboard.setupReady"
        @help="helpOpen = true" @login-hh="dashboard.openBrowser" @open-vnc="dashboard.openVnc"
        @save-browser="dashboard.saveBrowser" @add-resume="manualOpen = true" @sync-resumes="dashboard.syncResumes"
        @find-telegram-chats="dashboard.findTelegramChats"
        @logout="dashboard.logout" />
      <SetupAlert :issues="dashboard.setupIssues" />
      <p v-if="dashboard.message" class="message">{{ dashboard.message }}</p>
      <ResumeList :resumes="dashboard.resumes" :connected="dashboard.connected" :busy="dashboard.busy" :browser-saved="dashboard.browserSaved"
        @toggle-publishing="dashboard.togglePublishing" @toggle-monitoring="dashboard.toggleVacancyMonitoring"
        @toggle-response-limit="dashboard.toggleVacancyResponseLimit" @set-response-limit="dashboard.setVacancyResponseLimit"
        @publish="dashboard.publish" @ats="dashboard.checkAts" @collect="dashboard.collectVacancies"
        @history="dashboard.showHistory" @vacancies="dashboard.showVacancies" @remove="dashboard.removeResume" />
      <OperationHistory :rows="dashboard.history" @close="dashboard.history = []" />
      <VacancyStatistics :title="dashboard.vacancyTitle" :vacancies="dashboard.vacancies" @close="dashboard.vacancies = []; dashboard.vacancyTitle = ''" />
      <ManualResumeModal v-if="manualOpen" :busy="dashboard.busy" @close="manualOpen = false" @submit="addManualResume" />
      <HelpModal v-if="helpOpen" @close="helpOpen = false" />
    </template>
  </main>
</template>
