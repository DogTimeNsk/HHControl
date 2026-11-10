const formatter = new Intl.DateTimeFormat('ru-RU', {
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
})

export function formatDateTime(value: string | null): string {
  return value ? formatter.format(new Date(value)) : '—'
}
