<script setup lang="ts">
import { ref } from "vue";
import type { DayPlan } from "../types";

defineProps<{ day: DayPlan }>();

const isOpen = ref(false);

function formatDate(date?: string | null) {
  if (!date) return "待定";
  const parts = date.split("-");
  return parts.length === 3 ? `${parts[1]}/${parts[2]}` : date;
}
</script>

<template>
  <div :class="['day-card', { 'day-card--open': isOpen }]">
    <button class="day-card__head" @click="isOpen = !isOpen">
      <div class="day-card__head-left">
        <span class="day-card__day">Day {{ day.day_index }}</span>
        <span class="day-card__theme">{{ day.theme || "自由探索" }}</span>
      </div>
      <div class="day-card__head-right">
        <span class="day-card__date">{{ formatDate(day.date) }}</span>
        <span class="day-card__arrow">{{ isOpen ? "▾" : "▸" }}</span>
      </div>
    </button>

    <Transition name="fade">
      <div v-if="isOpen" class="day-card__body">
        <!-- Spots -->
        <div v-if="day.spots.length" class="day-card__section">
          <h4 class="day-card__section-title">景点</h4>
          <div class="day-card__items">
            <div v-for="spot in day.spots" :key="spot.name" class="day-card__item">
              <div class="day-card__item-name">{{ spot.name }}</div>
              <div v-if="spot.address" class="day-card__item-meta">{{ spot.address }}</div>
              <div v-if="spot.description" class="day-card__item-desc">{{ spot.description }}</div>
            </div>
          </div>
        </div>

        <!-- Meals -->
        <div v-if="day.meals.length" class="day-card__section">
          <h4 class="day-card__section-title">餐饮</h4>
          <div class="day-card__items">
            <div v-for="meal in day.meals" :key="meal.name" class="day-card__item">
              <div class="day-card__item-name">{{ meal.name }}</div>
              <div v-if="meal.address" class="day-card__item-meta">{{ meal.address }}</div>
            </div>
          </div>
        </div>

        <!-- Hotel -->
        <div v-if="day.hotel" class="day-card__section">
          <h4 class="day-card__section-title">住宿</h4>
          <div class="day-card__items">
            <div class="day-card__item">
              <div class="day-card__item-name">{{ day.hotel.name }}</div>
              <div v-if="day.hotel.address" class="day-card__item-meta">{{ day.hotel.address }}</div>
            </div>
          </div>
        </div>

        <!-- Transport -->
        <div v-if="day.transport.length" class="day-card__section">
          <h4 class="day-card__section-title">交通</h4>
          <div class="day-card__transport">
            <div v-for="t in day.transport" :key="t.mode + t.from_place" class="day-card__transport-item">
              <span class="day-card__transport-mode">{{ t.mode }}</span>
              <span v-if="t.from_place && t.to_place" class="day-card__transport-route">
                {{ t.from_place }} → {{ t.to_place }}
              </span>
              <span v-if="t.duration" class="day-card__transport-duration">{{ t.duration }}</span>
              <span v-if="t.distance_km != null" class="day-card__transport-duration">
                {{ t.distance_km.toFixed(1) }} km · {{ t.estimated_minutes || 0 }} min
              </span>
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div v-if="day.notes.length" class="day-card__section">
          <h4 class="day-card__section-title">备注</h4>
          <ul class="day-card__notes">
            <li v-for="(note, i) in day.notes" :key="i">{{ note }}</li>
          </ul>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.day-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: box-shadow var(--transition-base);
}

.day-card:hover {
  box-shadow: var(--shadow-sm);
}

.day-card--open {
  box-shadow: var(--shadow-sm);
}

.day-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 16px 20px;
  border: none;
  background: var(--color-surface);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.day-card__head:hover {
  background: var(--color-surface-subtle);
}

.day-card__head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.day-card__day {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-accent);
  letter-spacing: 0.02em;
}

.day-card__theme {
  font-size: 14px;
  color: var(--color-text-body);
}

.day-card__head-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.day-card__date {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.day-card__arrow {
  font-size: 12px;
  color: var(--color-text-secondary);
  transition: transform var(--transition-fast);
}

.day-card--open .day-card__arrow {
  color: var(--color-accent);
}

.day-card__body {
  padding: 0 20px 20px;
  border-top: 1px solid var(--color-divider);
}

.day-card__section {
  margin-top: 16px;
}

.day-card__section-title {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.day-card__items {
  display: grid;
  gap: 8px;
}

.day-card__item {
  padding: 10px 12px;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-sm);
}

.day-card__item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.day-card__item-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.day-card__item-desc {
  font-size: 13px;
  color: var(--color-text-body);
  margin-top: 4px;
  line-height: 1.5;
}

.day-card__transport {
  display: grid;
  gap: 6px;
}

.day-card__transport-item {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-sm);
  font-size: 13px;
  align-items: center;
}

.day-card__transport-mode {
  font-weight: 600;
  color: var(--color-accent);
}

.day-card__transport-route {
  color: var(--color-text-body);
}

.day-card__transport-duration {
  color: var(--color-text-secondary);
  margin-left: auto;
}

.day-card__notes {
  padding-left: 20px;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.8;
}
</style>
