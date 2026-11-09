export type Resume = {
  id: number
  title: string
  hh_resume_id: string
  enabled: boolean
  status: string | null
  published_at: string | null
  next_publish_at: string | null
  publish_available: boolean | null
  ats_achievements: boolean | null
  ats_checked_at: string | null
  last_error: string | null
  vacancy_monitoring_enabled: boolean
  vacancy_response_limit_enabled: boolean
  vacancy_response_limit: number
  last_vacancy_check_at: string | null
}

export type Vacancy = {
  id: number
  hh_vacancy_id: string
  title: string
  vacancy_url: string
  employer_name: string | null
  employer_url: string | null
  salary_from: number | null
  salary_to: number | null
  salary_currency: string | null
  salary_gross: boolean | null
  city: string | null
  responses_count: number | null
  total_responses_count: number | null
  online_users_count: number | null
  user_test_present: boolean | null
  user_test_id: string | null
  accept_temporary: boolean | null
  work_formats: string[]
  company_negative_attributes: Record<string, unknown> | null
  vacancy_properties: Record<string, unknown>[]
  parsed_at: string
  last_seen_at: string
}

export type SetupIssue = { code: string; message: string; help: string }
export type PublishEvent = { started_at: string; operation: string; result: string; message: string }
