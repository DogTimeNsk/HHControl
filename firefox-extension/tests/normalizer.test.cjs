const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "normalizer.js"), "utf8");
const context = { globalThis: {} };
vm.runInNewContext(source, context);
const inspector = context.globalThis.HHVacancyInspector;

test("finds the current vacancy and normalizes details used in HH Control", () => {
  const state = { page: { vacancy: {
    vacancyId: "42", name: "Python developer", responsesCount: 3, totalResponsesCount: 7,
    online_users_count: 2, userTestPresent: true, userTestId: "test-1", acceptTemporary: false,
    compensation: { from: 100000, currencyCode: "RUR", gross: false },
    company: { visibleName: "Acme", employersNegativeAttribute: { employerId: "1", suspicious: true } },
    address: { city: "Новосибирск" }, workFormats: [{ workFormatsElement: ["REMOTE"] }],
    vacancyProperties: { properties: [{ property: [{ propertyType: "ANTIFRAUD", enabled: true }] }] },
    newHhField: "observed"
  } } };
  const vacancy = inspector.findVacancy(state, "42");
  const result = inspector.normalize(vacancy);
  assert.equal(result.title, "Python developer");
  assert.equal(result.responsesCount, 3);
  assert.deepEqual(JSON.parse(JSON.stringify(result.workFormats)), ["REMOTE"]);
  assert.equal(result.properties[0].type, "ANTIFRAUD");
  assert.deepEqual(JSON.parse(JSON.stringify(result.unknown)), [{ key: "newHhField", value: "observed" }]);
});

test("does not pick a vacancy with another id", () => {
  const state = { vacancySearchResult: { vacancies: [{ vacancyId: "11", name: "Other" }] } };
  assert.equal(inspector.findVacancy(state, "42"), null);
  assert.equal(inspector.vacancyIdFromLocation("/vacancy/42"), "42");
});

test("reads live counters stored next to the vacancy page payload", () => {
  const state = {
    vacancyView: { vacancyFull: {
      vacancy: { vacancyId: 42, name: "Live vacancy", vacancyProperties: { properties: [
        { propertyType: "HH_STANDARD" }
      ] } },
      extraVacancyFields: { vacancyResponsesCount: 109, totalResponsesCount: 109 }
    } },
    vacancyOnlineUsersCounters: { "42": { includingCurrent: 161, excludingCurrent: 160 } }
  };
  const result = inspector.normalizeState(state, "42");
  assert.equal(result.responsesCount, 109);
  assert.equal(result.totalResponsesCount, 109);
  assert.equal(result.onlineUsersCount, 161);
  assert.equal(result.properties[0].type, "HH_STANDARD");
});
