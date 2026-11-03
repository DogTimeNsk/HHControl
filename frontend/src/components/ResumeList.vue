<script setup lang="ts">
import ResumeCard from './ResumeCard.vue'
import type { Resume } from '../types'

defineProps<{ resumes: Resume[]; connected: boolean; busy: boolean; browserSaved: boolean }>()
const emit = defineEmits<{
  togglePublishing: [resume: Resume]
  toggleMonitoring: [resume: Resume]
  publish: [resume: Resume]
  ats: [resume: Resume]
  collect: [resume: Resume]
  history: [resume: Resume]
  vacancies: [resume: Resume]
  remove: [resume: Resume]
}>()
</script>

<template>
  <section class="card resume-list">
    <div v-if="!resumes.length" class="empty">{{ connected ? 'Резюме ещё не синхронизированы.' : 'Подключите аккаунт hh.ru.' }}</div>
    <ResumeCard v-for="resume in resumes" :key="resume.id" :resume="resume" :busy="busy" :browser-saved="browserSaved"
      @toggle-publishing="emit('togglePublishing', resume)" @toggle-monitoring="emit('toggleMonitoring', resume)"
      @publish="emit('publish', resume)" @ats="emit('ats', resume)" @collect="emit('collect', resume)"
      @history="emit('history', resume)" @vacancies="emit('vacancies', resume)" @remove="emit('remove', resume)" />
  </section>
</template>
