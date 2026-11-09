import { proxyRefs, ref } from 'vue'

import { api } from '../services/api'
import type { PublishEvent, Resume, SetupIssue, Vacancy } from '../types'
import { formatDateTime } from '../utils/date'

type TelegramChat = { id: number; type: string; name: string; username: string }

export function useDashboard() {
  const loggedIn = ref(false)
  const username = ref('admin')
  const password = ref('')
  const resumes = ref<Resume[]>([])
  const connected = ref(false)
  const browserSaved = ref(false)
  const setupReady = ref(false)
  const setupIssues = ref<SetupIssue[]>([])
  const message = ref('')
  const busy = ref(false)
  const history = ref<string[]>([])
  const vacancies = ref<Vacancy[]>([])
  const vacancyTitle = ref('')

  async function action(callback: () => Promise<void>) {
    try {
      busy.value = true
      await callback()
    } catch (error) {
      message.value = (error as Error).message
    } finally {
      busy.value = false
    }
  }

  async function load() {
    const setup = await api.get<{ ready: boolean; issues: SetupIssue[] }>('/setup/status')
    setupReady.value = setup.ready
    setupIssues.value = setup.issues
    resumes.value = await api.get<Resume[]>('/resumes')
    connected.value = (await api.get<{ connected: boolean }>('/connection')).connected
    browserSaved.value = (await api.get<{ saved: boolean }>('/browser/session')).saved
  }

  async function login() {
    try {
      await api.post('/auth/login', { username: username.value, password: password.value })
      loggedIn.value = true
      password.value = ''
      await load()
    } catch (error) {
      message.value = (error as Error).message
    }
  }

  async function logout() {
    await api.post('/auth/logout')
    loggedIn.value = false
  }

  async function openBrowser() {
    await action(async () => {
      await api.post('/browser/open')
      window.open('/browser/vnc.html?autoconnect=true&path=browser/websockify', '_blank')
    })
  }

  function openVnc() {
    window.open('/browser/vnc.html?autoconnect=true&path=browser/websockify', '_blank', 'noopener')
  }

  async function saveBrowser() {
    await action(async () => {
      await api.post('/browser/session/save')
      browserSaved.value = true
      message.value = 'Browser session сохранена. Теперь синхронизация использует личный кабинет HH.'
    })
  }

  async function syncResumes() {
    await action(async () => {
      resumes.value = await api.post<Resume[]>('/resumes/sync')
      message.value = 'Список резюме синхронизирован.'
    })
  }

  async function findTelegramChats() {
    await action(async () => {
      const chats = await api.get<TelegramChat[]>('/telegram/chats')
      message.value = chats.length
        ? `Telegram chat_id: ${chats.map((chat) => `${chat.name} (${chat.id})`).join('; ')}`
        : 'Telegram пока не вернул чаты. Откройте диалог с ботом, отправьте /start и повторите.'
    })
  }

  async function addManualResume(hhResumeId: string) {
    await action(async () => {
      const resume = await api.post<Resume>('/resumes/manual', { hh_resume_id: hhResumeId })
      const index = resumes.value.findIndex((item) => item.id === resume.id)
      if (index >= 0) resumes.value[index] = resume
      else resumes.value.push(resume)
      message.value = 'Резюме подключено. Автообновление выключено.'
    })
  }

  async function togglePublishing(resume: Resume) {
    if (!setupReady.value) return
    await action(async () => {
      const updated = await api.patch<Resume>(`/resumes/${resume.id}`, { enabled: !resume.enabled })
      Object.assign(resume, updated)
    })
  }

  async function toggleVacancyMonitoring(resume: Resume) {
    if (!setupReady.value) return
    await action(async () => {
      const updated = await api.patch<Resume>(`/resumes/${resume.id}`, {
        vacancy_monitoring_enabled: !resume.vacancy_monitoring_enabled,
      })
      Object.assign(resume, updated)
    })
  }

  async function toggleVacancyResponseLimit(resume: Resume) {
    if (!setupReady.value || !resume.vacancy_monitoring_enabled) return
    await action(async () => {
      const updated = await api.patch<Resume>(`/resumes/${resume.id}`, {
        vacancy_response_limit_enabled: !resume.vacancy_response_limit_enabled,
      })
      Object.assign(resume, updated)
    })
  }

  async function setVacancyResponseLimit(resume: Resume, limit: number) {
    if (!setupReady.value || !resume.vacancy_monitoring_enabled || !Number.isInteger(limit) || limit < 1) return
    await action(async () => {
      const updated = await api.patch<Resume>(`/resumes/${resume.id}`, { vacancy_response_limit: limit })
      Object.assign(resume, updated)
    })
  }

  async function publish(resume: Resume) {
    if (!setupReady.value || !confirm(`Обновить «${resume.title}» сейчас?`)) return
    await action(async () => {
      const event = await api.post<{ message: string }>(`/resumes/${resume.id}/publish`)
      message.value = event.message
      await load()
    })
  }

  async function checkAts(resume: Resume) {
    if (!setupReady.value) return
    await action(async () => {
      const updated = await api.post<Resume>(`/resumes/${resume.id}/ats-check`)
      Object.assign(resume, updated)
      message.value = updated.ats_achievements
        ? 'Есть конкретные достижения — хороший сигнал для ATS.'
        : 'Плашка «Конкретные достижения» не найдена.'
    })
  }

  async function removeResume(resume: Resume) {
    if (!confirm(`Убрать «${resume.title}» из локального управления? На hh.ru оно останется.`)) return
    await action(async () => {
      await api.delete(`/resumes/${resume.id}`)
      resumes.value = resumes.value.filter((item) => item.id !== resume.id)
    })
  }

  async function showHistory(resume: Resume) {
    await action(async () => {
      const rows = await api.get<PublishEvent[]>(`/resumes/${resume.id}/history`)
      history.value = rows.map((row) => `${formatDateTime(row.started_at)} — ${row.operation}/${row.result}: ${row.message}`)
    })
  }

  async function showVacancies(resume: Resume) {
    await action(async () => {
      vacancies.value = await api.get<Vacancy[]>(`/resumes/${resume.id}/vacancies`)
      vacancyTitle.value = resume.title
    })
  }

  async function collectVacancies(resume: Resume) {
    if (!setupReady.value) return
    await action(async () => {
      const result = await api.post<{ new_count: number }>(`/resumes/${resume.id}/vacancies/collect`)
      vacancies.value = await api.get<Vacancy[]>(`/resumes/${resume.id}/vacancies`)
      vacancyTitle.value = resume.title
      message.value = `Сбор завершён: новых вакансий — ${result.new_count}.`
      await load()
    })
  }

  return proxyRefs({
    loggedIn, username, password, resumes, connected, browserSaved, setupReady, setupIssues,
    message, busy, history, vacancies, vacancyTitle,
    load, login, logout, openBrowser, openVnc, saveBrowser, syncResumes, findTelegramChats, addManualResume,
    togglePublishing, toggleVacancyMonitoring, toggleVacancyResponseLimit, setVacancyResponseLimit,
    publish, checkAts, removeResume, showHistory,
    showVacancies, collectVacancies,
  })
}
