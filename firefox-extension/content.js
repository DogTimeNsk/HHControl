(() => {
  "use strict";

  const inspector = globalThis.HHVacancyInspector;
  const ROOT_ID = "hh-live-details-extension";

  function readState() {
    const node = document.querySelector("#HH-Lux-InitialState");
    if (!node) throw new Error("Блок HH-Lux-InitialState пока не найден");
    const raw = node.content ? node.content.textContent : node.textContent;
    if (!raw || !raw.trim()) throw new Error("HH-Lux-InitialState пуст");
    return JSON.parse(raw);
  }

  function salaryText(salary) {
    if (salary.from === null && salary.to === null) return "не указана";
    const formatter = new Intl.NumberFormat("ru-RU");
    const parts = [];
    if (salary.from !== null) parts.push(`от ${formatter.format(salary.from)}`);
    if (salary.to !== null) parts.push(`до ${formatter.format(salary.to)}`);
    if (salary.currency) parts.push(salary.currency);
    if (salary.gross !== null) parts.push(salary.gross ? "до вычета налогов" : "на руки");
    return parts.join(" · ");
  }

  function activeNegativeAttributes(attributes) {
    return Object.entries(attributes)
      .filter(([key, value]) => key !== "employerId" && key !== "creationDate" && value === true)
      .map(([key]) => key);
  }

  function row(label, value) {
    return `<div class="hh-live-details__row"><dt>${label}</dt><dd>${value}</dd></div>`;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[char]));
  }

  function render(data) {
    const negative = activeNegativeAttributes(data.negativeAttributes);
    const properties = data.properties.map((item) => inspector.propertyLabel(item.type)).join(", ") || "—";
    const antiFraud = data.properties
      .filter((item) => item.type.includes("ANTIFRAUD"))
      .map((item) => escapeHtml(JSON.stringify(item.value))).join("<br>");
    const unknown = data.unknown.length
      ? data.unknown.map((item) => `<li><code>${escapeHtml(item.key)}</code>: ${escapeHtml(item.value)}</li>`).join("")
      : "<li>Неизвестных полей нет.</li>";

    return `
      <header class="hh-live-details__header">
        <strong>Актуальные данные HH</strong>
        <button type="button" class="hh-live-details__close" aria-label="Закрыть">×</button>
      </header>
      <p class="hh-live-details__caption">Состояние страницы сейчас, не снимок из HH Control.</p>
      <dl class="hh-live-details__list">
        ${row("Вакансия", escapeHtml(data.title))}
        ${row("Работодатель / город", escapeHtml([data.employer, data.city].filter(Boolean).join(" · ") || "—"))}
        ${row("Зарплата", escapeHtml(salaryText(data.salary)))}
        ${row("Отклики", `${data.responsesCount ?? "—"} / ${data.totalResponsesCount ?? "—"}`)}
        ${row("Смотрят сейчас", data.onlineUsersCount ?? "—")}
        ${row("Тест при отклике", inspector.formatValue(data.userTestPresent))}
        ${data.userTestId ? row("ID теста", escapeHtml(data.userTestId)) : ""}
        ${row("Временная работа", inspector.formatValue(data.acceptTemporary))}
        ${row("Форматы работы", escapeHtml(data.workFormats.join(", ") || "—"))}
        ${row("Негативные метки компании", escapeHtml(negative.join(", ") || "нет активных меток"))}
        ${row("Свойства HH", escapeHtml(properties))}
        ${antiFraud ? row("Антифрод", `<code>${antiFraud}</code>`) : ""}
      </dl>
      <details class="hh-live-details__unknown">
        <summary>Неизвестные ключи HH (${data.unknown.length})</summary>
        <ul>${unknown}</ul>
      </details>`;
  }

  function showError(error) {
    const panel = document.getElementById(ROOT_ID);
    panel.innerHTML = `<header class="hh-live-details__header"><strong>Данные HH</strong><button type="button" class="hh-live-details__close" aria-label="Закрыть">×</button></header><p class="hh-live-details__error">${escapeHtml(error.message)}</p>`;
    panel.querySelector(".hh-live-details__close").addEventListener("click", () => panel.remove());
  }

  function openPanel() {
    document.getElementById(ROOT_ID)?.remove();
    const panel = document.createElement("aside");
    panel.id = ROOT_ID;
    panel.className = "hh-live-details";
    document.body.append(panel);
    try {
      const id = inspector.vacancyIdFromLocation(location.pathname);
      const data = inspector.normalizeState(readState(), id);
      if (!data) throw new Error("Не удалось найти объект текущей вакансии в состоянии HH");
      panel.innerHTML = render(data);
      panel.querySelector(".hh-live-details__close").addEventListener("click", () => panel.remove());
    } catch (error) {
      showError(error instanceof Error ? error : new Error("Не удалось разобрать данные HH"));
    }
  }

  function addButton() {
    if (document.getElementById("hh-live-details-trigger")) return;
    const button = document.createElement("button");
    button.id = "hh-live-details-trigger";
    button.className = "hh-live-details__trigger";
    button.type = "button";
    button.textContent = "Данные HH";
    button.addEventListener("click", openPanel);
    document.body.append(button);
  }

  addButton();
  new MutationObserver(addButton).observe(document.documentElement, { childList: true, subtree: true });
})();
