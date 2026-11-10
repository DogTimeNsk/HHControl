(() => {
  "use strict";

  const KNOWN_KEYS = new Set([
    "vacancyId", "id", "name", "title", "compensation", "company", "address", "links",
    "responsesCount", "totalResponsesCount", "online_users_count", "onlineUsersCount",
    "userTestPresent", "userTestId", "acceptTemporary", "workFormats", "vacancyProperties",
    "employersNegativeAttribute", "employerNegativeAttributes", "description", "keySkills",
    "publishedAt", "creationDate", "professionalRoles", "experience", "employment",
    "schedule", "workingHours", "workScheduleByDays", "vacancyType", "archived"
  ]);

  const PROPERTY_LABELS = {
    "ANTIFRAUD": "Антифрод",
    "INCOMPLETE_COMPANY_INFO": "Неполные сведения о компании",
    "SUSPICIOUS": "Подозрительная вакансия"
  };

  function asObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function asNumber(value) {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }

  function asBoolean(value) {
    return typeof value === "boolean" ? value : null;
  }

  function formatValue(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "boolean") return value ? "Да" : "Нет";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function vacancyIdFromLocation(pathname) {
    const match = /^\/vacancy\/(\d+)(?:\/|$)/.exec(pathname || "");
    return match ? match[1] : null;
  }

  function scoreCandidate(value, vacancyId) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return -1;
    const id = String(value.vacancyId || value.id || "");
    // On a vacancy page the URL is the authoritative identity.  Never expose
    // a neighbouring recommendation or a cached search-result item instead.
    if (vacancyId && id && id !== vacancyId) return -1;
    let score = id && id === vacancyId ? 100 : 0;
    if (value.vacancyId) score += 10;
    if (value.responsesCount !== undefined) score += 5;
    if (value.vacancyProperties) score += 5;
    if (value.company) score += 3;
    if (value.compensation) score += 3;
    return score;
  }

  function findVacancy(state, vacancyId) {
    let best = null;
    let bestScore = -1;
    const visited = new WeakSet();

    function visit(value, depth) {
      if (!value || typeof value !== "object" || depth > 8 || visited.has(value)) return;
      visited.add(value);
      const score = scoreCandidate(value, vacancyId);
      if (score > bestScore) {
        best = value;
        bestScore = score;
      }
      const entries = Array.isArray(value) ? value : Object.values(value);
      for (const child of entries) visit(child, depth + 1);
    }

    visit(state, 0);
    return bestScore >= 10 ? best : null;
  }

  function workFormats(value) {
    if (!Array.isArray(value)) return [];
    return value.flatMap((group) => {
      if (typeof group === "string") return [group];
      const object = asObject(group);
      const elements = object.workFormatsElement || object.workFormats || [];
      return Array.isArray(elements) ? elements.map(String) : [];
    });
  }

  function properties(value) {
    const groups = asObject(value).properties;
    if (!Array.isArray(groups)) return [];
    return groups.flatMap((group) => {
      if (group && typeof group === "object" && group.propertyType) return [group];
      const property = asObject(group).property;
      return Array.isArray(property) ? property.filter((item) => item && typeof item === "object") : [];
    });
  }

  function normalize(vacancy) {
    const company = asObject(vacancy.company);
    const compensation = asObject(vacancy.compensation);
    const address = asObject(vacancy.address);
    const rawProperties = properties(vacancy.vacancyProperties);
    const negative = company.employersNegativeAttribute || company.employerNegativeAttributes || vacancy.employersNegativeAttribute;
    const unknown = Object.entries(vacancy)
      .filter(([key]) => !KNOWN_KEYS.has(key))
      .map(([key, value]) => ({ key, value: formatValue(value) }));

    return {
      id: String(vacancy.vacancyId || vacancy.id || ""),
      title: String(vacancy.name || vacancy.title || "Без названия"),
      employer: company.visibleName || company.name || null,
      city: address.city || address.raw || null,
      salary: {
        from: asNumber(compensation.from), to: asNumber(compensation.to),
        currency: compensation.currencyCode || compensation.currency || null,
        gross: asBoolean(compensation.gross)
      },
      responsesCount: asNumber(vacancy.responsesCount),
      totalResponsesCount: asNumber(vacancy.totalResponsesCount),
      onlineUsersCount: asNumber(vacancy.online_users_count ?? vacancy.onlineUsersCount),
      userTestPresent: asBoolean(vacancy.userTestPresent),
      userTestId: vacancy.userTestId || null,
      acceptTemporary: asBoolean(vacancy.acceptTemporary),
      workFormats: workFormats(vacancy.workFormats),
      negativeAttributes: asObject(negative),
      properties: rawProperties.map((property) => ({
        type: String(property.propertyType || property.type || "UNKNOWN"), value: property
      })),
      unknown
    };
  }

  function normalizeState(state, vacancyId) {
    const vacancyPage = asObject(asObject(state).vacancyView).vacancyFull;
    const page = asObject(vacancyPage);
    const vacancy = asObject(page.vacancy);
    const selected = String(vacancy.vacancyId || vacancy.id || "") === String(vacancyId)
      ? vacancy
      : findVacancy(state, vacancyId);
    if (!selected) return null;

    const result = normalize(selected);
    // Unlike a search card, the vacancy page stores volatile counters beside
    // the vacancy payload. Those values are refreshed by HH independently.
    const extra = asObject(page.extraVacancyFields);
    const counters = asObject(asObject(state).vacancyOnlineUsersCounters);
    const online = asObject(counters[String(vacancyId)]);
    result.responsesCount = asNumber(extra.vacancyResponsesCount ?? extra.responsesCount)
      ?? result.responsesCount;
    result.totalResponsesCount = asNumber(extra.totalResponsesCount) ?? result.totalResponsesCount;
    result.onlineUsersCount = asNumber(online.includingCurrent ?? online.excludingCurrent)
      ?? result.onlineUsersCount;
    return result;
  }

  function propertyLabel(type) {
    return PROPERTY_LABELS[type] || type;
  }

  globalThis.HHVacancyInspector = {
    findVacancy, formatValue, normalize, normalizeState, propertyLabel, vacancyIdFromLocation
  };
})();
