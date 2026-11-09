<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { Vacancy } from '../types'
import { formatDateTime } from '../utils/date'

const props = defineProps<{ title: string; vacancies: Vacancy[] }>()
const emit = defineEmits<{ close: [] }>()
const pageSize = 10
const currentPage = ref(1)
const pageCount = computed(() => Math.ceil(props.vacancies.length / pageSize))
const visibleVacancies = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return props.vacancies.slice(start, start + pageSize)
})

watch(() => props.vacancies, () => { currentPage.value = 1 })
watch(pageCount, (count) => {
  if (count && currentPage.value > count) currentPage.value = count
})

const flag = (value: boolean | null) => value === null ? 'неизвестно' : value ? 'да' : 'нет'
const salary = (vacancy: Vacancy) => {
  if (vacancy.salary_from === null && vacancy.salary_to === null) return 'не указана'
  const money = new Intl.NumberFormat('ru-RU')
  return `${vacancy.salary_from !== null ? `от ${money.format(vacancy.salary_from)}` : ''}${vacancy.salary_from !== null && vacancy.salary_to !== null ? ' ' : ''}${vacancy.salary_to !== null ? `до ${money.format(vacancy.salary_to)}` : ''} ${vacancy.salary_currency || ''}`.trim()
}
const propertyTypes = (vacancy: Vacancy) => vacancy.vacancy_properties.map((property) => String(property.propertyType || '')).filter(Boolean)
const antiFraud = (vacancy: Vacancy) => vacancy.vacancy_properties.filter((property) => String(property.propertyType || '').includes('ANTIFRAUD')).map((property) => JSON.stringify(property))
const negatives = (vacancy: Vacancy) => vacancy.company_negative_attributes
  ? Object.entries(vacancy.company_negative_attributes).filter(([key, value]) => key !== 'employerId' && key !== 'creationDate' && value === true).map(([key]) => key).join(', ') || 'нет активных меток'
  : 'не указаны'
</script>

<template>
  <section v-if="title" class="card history">
    <div class="section-heading"><h2>Подходящие вакансии: {{ title }}</h2><button class="icon-button secondary" aria-label="Закрыть статистику" @click="emit('close')">×</button></div>
    <p v-if="!vacancies.length">Пока ничего не собрано. Включите сбор и дождитесь следующего почасового запуска.</p>
    <article v-for="vacancy in visibleVacancies" :key="vacancy.id" class="vacancy">
      <a :href="vacancy.vacancy_url" target="_blank" rel="noopener">{{ vacancy.title }}</a>
      <div><a v-if="vacancy.employer_url" :href="vacancy.employer_url" target="_blank" rel="noopener">{{ vacancy.employer_name }}</a><span v-else>{{ vacancy.employer_name || 'Компания не указана' }}</span> · {{ vacancy.city || 'город не указан' }}</div>
      <div>Зарплата: {{ salary(vacancy) }}{{ vacancy.salary_gross === null ? '' : vacancy.salary_gross ? ', до вычета налогов' : ', на руки' }} · Впервые: {{ formatDateTime(vacancy.parsed_at) }}</div>
      <details><summary>Посмотреть подробности</summary><dl class="vacancy-details">
        <div><dt>Отклики</dt><dd>{{ vacancy.responses_count ?? '—' }} / {{ vacancy.total_responses_count ?? '—' }}</dd></div>
        <div><dt>Смотрят сейчас</dt><dd>{{ vacancy.online_users_count ?? '—' }}</dd></div>
        <div><dt>Тест при отклике</dt><dd>{{ flag(vacancy.user_test_present) }}</dd></div>
        <div><dt>Временная работа</dt><dd>{{ flag(vacancy.accept_temporary) }}</dd></div>
        <div><dt>Форматы работы</dt><dd>{{ vacancy.work_formats.join(', ') || '—' }}</dd></div>
        <div><dt>Последний раз найдено</dt><dd>{{ formatDateTime(vacancy.last_seen_at) }}</dd></div>
        <div><dt>Негативные метки компании</dt><dd>{{ negatives(vacancy) }}</dd></div>
        <div><dt>Свойства HH</dt><dd>{{ propertyTypes(vacancy).join(', ') || '—' }}</dd></div>
        <div v-if="antiFraud(vacancy).length"><dt>Антифрод</dt><dd class="raw">{{ antiFraud(vacancy).join('; ') }}</dd></div>
      </dl></details>
    </article>
    <nav v-if="pageCount > 1" class="pagination" aria-label="Страницы подходящих вакансий">
      <button class="secondary" :disabled="currentPage === 1" @click="currentPage -= 1">Назад</button>
      <span>Страница {{ currentPage }} из {{ pageCount }}</span>
      <button class="secondary" :disabled="currentPage === pageCount" @click="currentPage += 1">Вперёд</button>
    </nav>
  </section>
</template>
