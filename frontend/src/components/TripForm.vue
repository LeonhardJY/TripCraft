<script setup lang="ts">
import { reactive, computed } from "vue";
import { useRouter } from "vue-router";
import { useTripStore } from "../stores/trip";
import type { TripRequestPayload } from "../types";

const store = useTripStore();
const router = useRouter();

const today = new Date();
const plus2 = new Date(today);
plus2.setDate(plus2.getDate() + 2);

function fmt(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const form = reactive({
  destination: "大理",
  startDate: fmt(today),
  endDate: fmt(plus2),
  travelers: 2,
  budget: 3200,
  hotelLevel: "舒适型",
  pace: "轻松",
  preferences: ["自然风景", "拍照", "美食"],
  dietaryPreferences: ["少辣"],
  notes: "不想太早起床，希望安排一个适合看日落的地点。",
});

const dayCount = computed(() => {
  const s = new Date(form.startDate);
  const e = new Date(form.endDate);
  const diff = e.getTime() - s.getTime();
  return Number.isNaN(diff) ? 0 : Math.max(Math.floor(diff / 86400000) + 1, 0);
});

const prefs = ["自然风景", "拍照", "美食", "古镇", "休闲"];
const diets = ["少辣", "不吃香菜", "不吃葱"];

function toggle<T>(list: T[], v: T) {
  const i = list.indexOf(v);
  i >= 0 ? list.splice(i, 1) : list.push(v);
}

function setDestination(city: string) {
  form.destination = city;
}

async function submit() {
  store.clearError();
  const p: TripRequestPayload = {
    destination: form.destination,
    start_date: form.startDate,
    end_date: form.endDate,
    travelers: form.travelers,
    budget: form.budget,
    preferences: form.preferences,
    pace: form.pace,
    hotel_level: form.hotelLevel,
    dietary_preferences: form.dietaryPreferences,
    special_notes: form.notes || null,
  };
  try {
    await store.generateTrip(p);
    router.push({ name: "result" });
  } catch { /* handled */ }
}

defineExpose({ setDestination });
</script>

<template>
  <form class="planner" @submit.prevent="submit">
    <!-- 第一行：目的地 + 日期 -->
    <div class="planner__main">
      <div class="planner__field planner__field--dest">
        <label class="planner__label">目的地</label>
        <input
          v-model="form.destination"
          class="planner__input"
          placeholder="城市名称"
          required
        />
      </div>

      <div class="planner__field">
        <label class="planner__label">日期</label>
        <div class="planner__dates">
          <input v-model="form.startDate" type="date" class="planner__input planner__input--date" />
          <span class="planner__date-sep">–</span>
          <input v-model="form.endDate" type="date" class="planner__input planner__input--date" />
        </div>
      </div>
    </div>

    <!-- 第二行：人数 + 预算 + 住宿 -->
    <div class="planner__row">
      <div class="planner__field">
        <label class="planner__label">人数</label>
        <input v-model.number="form.travelers" type="number" min="1" class="planner__input" />
      </div>
      <div class="planner__field">
        <label class="planner__label">预算（元）</label>
        <input v-model.number="form.budget" type="number" min="0" class="planner__input" placeholder="总预算" />
      </div>
      <div class="planner__field">
        <label class="planner__label">住宿</label>
        <select v-model="form.hotelLevel" class="planner__input planner__select">
          <option value="经济型">经济型</option>
          <option value="舒适型">舒适型</option>
          <option value="高档型">高档型</option>
        </select>
      </div>
    </div>

    <!-- 第三行：节奏 + 天数 -->
    <div class="planner__row">
      <div class="planner__field">
        <label class="planner__label">节奏</label>
        <select v-model="form.pace" class="planner__input planner__select">
          <option value="轻松">悠闲 · 慢节奏</option>
          <option value="适中">适中 · 劳逸结合</option>
          <option value="紧凑">紧凑 · 行程充实</option>
        </select>
      </div>
      <div class="planner__field">
        <label class="planner__label">天数</label>
        <div class="planner__meter">
          <div class="planner__meter-track">
            <div class="planner__meter-fill" :style="{ width: `${Math.min(dayCount / 14 * 100, 100)}%` }" />
          </div>
          <span class="planner__meter-label">{{ dayCount }} 天</span>
        </div>
      </div>
      <div class="planner__field" />
    </div>

    <!-- 偏好 -->
    <div class="planner__chips">
      <span class="planner__chips-label">风格偏好</span>
      <button v-for="o in prefs" :key="o" type="button"
        :class="['chip chip--sm', { 'chip--active': form.preferences.includes(o) }]"
        @click="toggle(form.preferences, o)">{{ o }}</button>
    </div>

    <div class="planner__chips">
      <span class="planner__chips-label">饮食偏好</span>
      <button v-for="o in diets" :key="o" type="button"
        :class="['chip chip--sm', { 'chip--active': form.dietaryPreferences.includes(o) }]"
        @click="toggle(form.dietaryPreferences, o)">{{ o }}</button>
    </div>

    <!-- 补充说明 -->
    <div class="planner__field">
      <label class="planner__label">补充说明</label>
      <textarea v-model="form.notes" class="planner__input planner__textarea" rows="2"
        placeholder="不想太早起床 / 想看日落 / 有特殊饮食要求……"></textarea>
    </div>

    <!-- Error -->
    <div v-if="store.generateError" class="planner__error">
      {{ store.generateError }}
    </div>

    <!-- Submit -->
    <button type="submit" class="planner__go" :disabled="store.isGenerating">
      <span v-if="store.isGenerating" class="spinner" />
      {{ store.isGenerating ? "规划中…" : "开启旅程" }}
    </button>
  </form>
</template>

<style scoped>
.planner {
  display: grid;
  gap: 14px;
}

.planner__main {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 12px;
}

.planner__row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.planner__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.planner__label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.planner__input {
  width: 100%;
  padding: 10px 12px;
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--color-text-primary);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.planner__input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(217, 119, 87, 0.12);
}

.planner__input::placeholder {
  color: var(--color-text-placeholder);
}

.planner__select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%238C8478' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 28px;
  cursor: pointer;
}

.planner__textarea {
  resize: vertical;
  min-height: 56px;
  line-height: 1.6;
  font-family: var(--font-body);
}

.planner__dates {
  display: flex;
  align-items: center;
  gap: 6px;
}

.planner__input--date {
  flex: 1;
  min-width: 0;
}

.planner__date-sep {
  color: var(--color-text-placeholder);
  font-size: 14px;
  flex-shrink: 0;
}

/* Day meter */
.planner__meter {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

.planner__meter-track {
  flex: 1;
  height: 3px;
  background: var(--color-surface-subtle);
  border-radius: 999px;
  overflow: hidden;
}

.planner__meter-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-accent), #3A7D5C);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.planner__meter-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* Chips row */
.planner__chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.planner__chips-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 4px;
  white-space: nowrap;
}

/* Error */
.planner__error {
  padding: 10px 14px;
  background: var(--color-danger-light);
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: 13px;
}

/* Submit */
.planner__go {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px 24px;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  background: var(--color-accent);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  letter-spacing: 0.01em;
  transition: background var(--transition-fast), transform var(--transition-fast);
}

.planner__go:hover {
  background: var(--color-accent-hover);
}

.planner__go:active {
  transform: scale(0.98);
}

.planner__go:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 640px) {
  .planner__main,
  .planner__row {
    grid-template-columns: 1fr;
  }
}
</style>
