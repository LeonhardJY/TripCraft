<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useTripStore } from "../stores/trip";
import { saveTrip, getMarkdownExportUrl, getPdfExportUrl } from "../services/api";
import TripMap from "../components/TripMap.vue";
import SmartEditor from "../components/SmartEditor.vue";
import DayPlanCard from "../components/DayPlanCard.vue";

const store = useTripStore();
const router = useRouter();

const saving = ref(false);
const exporting = ref<"pdf" | "md" | null>(null);
const it = computed(() => store.currentItinerary);

const budgetItems = computed(() => {
  const b = it.value?.budget_breakdown;
  if (!b) return [];
  return [
    { label: "门票", value: b.tickets, color: "#D97757" },
    { label: "住宿", value: b.hotel, color: "#3A7D5C" },
    { label: "餐饮", value: b.meals, color: "#B8873A" },
    { label: "交通", value: b.transport, color: "#5B7DB8" },
    { label: "其他", value: b.other, color: "#8C8478" },
  ];
});

const total = computed(() => it.value?.estimated_budget ?? 0);
const maxBudget = computed(() => Math.max(...budgetItems.value.map((b) => b.value), 1));

const mapPoints = computed(() => {
  if (!it.value) return [];
  return it.value.days.flatMap((d) =>
    d.spots.map((s) => ({
      key: `${d.day_index}-${s.name}`,
      dayIndex: d.day_index,
      date: d.date || "",
      theme: d.theme || "",
      name: s.name,
      address: s.address || s.location || "",
      latitude: s.latitude,
      longitude: s.longitude,
      poiId: s.poi_id,
      imageUrl: s.image_url,
      description: s.description || "",
    }))
  );
});

const techKeywords = ["LLM", "RAG", "LangChain", "Chroma", "演示", "测试", "模型", "源码"];
const tips = computed(() => {
  if (!it.value) return [];
  return it.value.tips
    .map((t) => t.trim())
    .filter(Boolean)
    .filter((t) => !techKeywords.some((k) => t.includes(k)));
});

function buildPayload() {
  if (!it.value) return null;
  return { ...it.value, tips: tips.value };
}

async function handleSave() {
  const p = buildPayload();
  if (!p) return;
  saving.value = true;
  try { await saveTrip(p); } finally { saving.value = false; }
}

async function handleExport(fmt: "pdf" | "md") {
  const p = buildPayload();
  if (!p) return;
  const win = window.open("about:blank", "_blank");
  exporting.value = fmt;
  try {
    await saveTrip(p);
    const url = fmt === "pdf" ? getPdfExportUrl(p.trip_id) : getMarkdownExportUrl(p.trip_id);
    if (win) win.location.href = url;
  } catch { win?.close(); }
  finally { exporting.value = null; }
}

function fmtDate(d?: string | null) {
  if (!d) return "";
  const p = d.split("-");
  return p.length === 3 ? `${p[0]}年${p[1]}月${p[2]}日` : d;
}
</script>

<template>
  <div v-if="it" class="result">
    <!-- Hero -->
    <section class="result-hero">
      <div class="result-hero__bg" />
      <div class="section result-hero__inner">
        <p class="result-hero__eyebrow">{{ it.destination }} · Travel Plan</p>
        <h1 class="result-hero__title">{{ it.destination }}旅行计划</h1>
        <p class="result-hero__meta">
          {{ fmtDate(it.days[0]?.date) }} — {{ fmtDate(it.days[it.days.length - 1]?.date) }}
          · {{ it.days.length }} 天
        </p>
      </div>
    </section>

    <div class="section" style="padding-bottom: var(--spacing-16)">
      <!-- Action Bar -->
      <div class="result-bar" v-reveal>
        <div class="result-bar__left">
          <button class="btn btn--ghost btn--sm" @click="router.push({ name: 'home' })">
            ← 新建规划
          </button>
          <button class="btn btn--sm" :disabled="saving" @click="handleSave">
            {{ saving ? "保存中…" : "保存" }}
          </button>
          <button class="btn btn--sm" :disabled="exporting === 'pdf'" @click="handleExport('pdf')">
            {{ exporting === 'pdf' ? "导出中…" : "导出 PDF" }}
          </button>
          <button class="btn btn--sm" :disabled="exporting === 'md'" @click="handleExport('md')">
            {{ exporting === 'md' ? "导出中…" : "Markdown" }}
          </button>
        </div>
      </div>

      <!-- Summary -->
      <div class="card" v-reveal>
        <p style="font-size: 15px; line-height: 1.8;">{{ it.summary }}</p>
        <div v-if="tips.length" class="tips-block">
          <span class="tips-block__label">出行提示</span>
          <ul>
            <li v-for="(t, i) in tips" :key="i">{{ t }}</li>
          </ul>
        </div>
      </div>

      <!-- Budget -->
      <div class="card" style="margin-top: var(--spacing-4)" v-reveal>
        <h3 class="card__header">预算明细</h3>
        <div class="budget-chart">
          <div v-for="item in budgetItems" :key="item.label" class="budget-row">
            <div class="budget-row__label">
              <span class="budget-row__dot" :style="{ background: item.color }" />
              <span>{{ item.label }}</span>
            </div>
            <div class="budget-row__track">
              <div
                class="budget-row__bar"
                :style="{ width: `${(item.value / maxBudget) * 100}%`, background: item.color }"
              />
            </div>
            <span class="budget-row__value">¥{{ item.value.toFixed(0) }}</span>
          </div>
        </div>
        <div class="budget-total">
          <span>预估总费用</span>
          <strong>¥{{ total.toFixed(0) }}</strong>
        </div>
      </div>

      <!-- Map + Weather split -->
      <div class="split-row" v-reveal>
        <div class="card split-main">
          <h3 class="card__header">景点地图</h3>
          <div style="height: 320px">
            <TripMap :points="mapPoints" />
          </div>
        </div>
        <div class="card split-side">
          <h3 class="card__header">天气</h3>
          <div v-if="store.isWeatherLoading" class="split-skel">
            <div v-for="i in 5" :key="i" class="skeleton skeleton--text" :style="{ width: `${60 + i * 8}%` }" />
          </div>
          <div v-else-if="store.weatherError" class="text-sm text-muted">{{ store.weatherError }}</div>
          <div v-else-if="store.weather" class="weather-list">
            <div v-for="d in store.weather.days" :key="d.date || d.week" class="weather-row">
              <div class="weather-row__date">
                <span class="weather-row__week">{{ d.week || "" }}</span>
                <span class="weather-row__day">{{ d.date?.slice(5) || "" }}</span>
              </div>
              <div class="weather-row__temps">
                <span class="weather-row__high">{{ d.day_temp || "-" }}°</span>
                <span class="weather-row__low">{{ d.night_temp || "-" }}°</span>
              </div>
              <span class="weather-row__desc text-sm text-muted">{{ d.day_weather || "--" }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-muted">暂无天气数据</div>
        </div>
      </div>

      <!-- Day Plans -->
      <div class="card" v-reveal>
        <h3 class="card__header">每日行程</h3>
        <div class="day-list">
          <DayPlanCard v-for="day in it.days" :key="day.day_index" :day="day" />
        </div>
      </div>

      <!-- Smart Editor -->
      <div v-reveal>
        <SmartEditor />
      </div>

      <!-- Bottom bar -->
      <div class="result-bar" style="margin-top: var(--spacing-4)" v-reveal>
        <div class="result-bar__left">
          <button class="btn btn--ghost btn--sm" @click="router.push({ name: 'home' })">
            ← 新建规划
          </button>
          <button class="btn btn--primary btn--sm" @click="handleExport('pdf')">
            导出 PDF
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="result-empty">
    <div class="section" style="text-align: center; padding-top: 120px">
      <p class="text-muted">暂无行程数据</p>
      <button class="btn btn--primary" style="margin-top: var(--spacing-4)" @click="router.push({ name: 'home' })">
        开始规划
      </button>
    </div>
  </div>
</template>

<style scoped>
.result {
  padding-bottom: var(--spacing-10);
}

/* Card */
.card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--spacing-6);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.card__header {
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-5);
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--color-divider);
}

/* Tips */
.tips-block {
  margin-top: var(--spacing-5);
  padding: var(--spacing-4) var(--spacing-5);
  background: var(--color-surface-subtle);
  border-radius: var(--radius-sm);
}

.tips-block__label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: var(--spacing-2);
}

.tips-block ul {
  padding-left: 18px;
  font-size: 13px;
  color: var(--color-text-body);
  line-height: 1.8;
}

/* Budget chart */
.budget-chart {
  display: grid;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-5);
}

.budget-row {
  display: grid;
  grid-template-columns: 60px 1fr 80px;
  gap: 12px;
  align-items: center;
}

.budget-row__label {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: 13px;
  color: var(--color-text-body);
}

.budget-row__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.budget-row__track {
  height: 6px;
  background: var(--color-surface-subtle);
  border-radius: 999px;
  overflow: hidden;
}

.budget-row__bar {
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s ease;
}

.budget-row__value {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  text-align: right;
}

.budget-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-5);
  background: var(--color-text-primary);
  border-radius: var(--radius-sm);
  color: #fff;
  font-size: 14px;
}

.budget-total strong {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
}

/* Split row */
.split-row {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: var(--spacing-4);
  margin-top: var(--spacing-4);
}

.split-main {
  min-height: 320px;
}

.split-side {
  padding: var(--spacing-5);
}

.split-skel {
  display: grid;
  gap: var(--spacing-2);
}

/* Weather */
.weather-list {
  display: grid;
  gap: 2px;
}

.weather-row {
  display: grid;
  grid-template-columns: 50px 1fr;
  gap: var(--spacing-2);
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--color-divider);
  font-size: 13px;
}

.weather-row:last-child { border-bottom: none; }

.weather-row__date {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.weather-row__week {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.weather-row__day {
  font-size: 13px;
  color: var(--color-text-primary);
}

.weather-row__temps {
  display: flex;
  gap: var(--spacing-1);
}

.weather-row__high {
  font-weight: 600;
  color: var(--color-accent);
}

.weather-row__low {
  color: var(--color-text-secondary);
}

.weather-row__desc {
  grid-column: 1 / -1;
}

/* Day list */
.day-list {
  display: grid;
  gap: var(--spacing-3);
}

/* Empty */
.result-empty {
  min-height: 60vh;
}

@media (max-width: 768px) {
  .split-row {
    grid-template-columns: 1fr;
  }
  .budget-row {
    grid-template-columns: 50px 1fr 60px;
    gap: var(--spacing-2);
  }
}
</style>
