<script setup lang="ts">
import { ref, watch } from "vue";
import { useTripStore } from "../stores/trip";

const store = useTripStore();

const instruction = ref("这一天节奏更轻松一点，减少固定安排。");
const selectedDay = ref(1);
const isOpen = ref(false);

watch(
  () => store.currentItinerary?.days,
  (days) => {
    if (days?.length) selectedDay.value = days[0].day_index;
  },
  { immediate: true }
);

async function handleEdit() {
  if (!instruction.value.trim()) return;
  await store.editTrip(instruction.value, selectedDay.value);
}
</script>

<template>
  <div class="smart-editor">
    <button class="smart-editor__toggle" @click="isOpen = !isOpen">
      <span class="smart-editor__toggle-icon">{{ isOpen ? "▾" : "▸" }}</span>
      <span>智能调整行程</span>
      <span class="text-muted text-sm">用自然语言修改某一天</span>
    </button>

    <div v-if="isOpen" class="smart-editor__body">
      <div class="smart-editor__row">
        <div class="form-group" style="margin-bottom: 0; flex: 1">
          <label class="form-label">选择日期</label>
          <select v-model="selectedDay" class="form-select">
            <option
              v-for="day in store.currentItinerary?.days"
              :key="day.day_index"
              :value="day.day_index"
            >
              第 {{ day.day_index }} 天 · {{ day.theme || "未设定" }}
            </option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom: 0">
          <label class="form-label">&nbsp;</label>
          <button
            class="btn btn--primary"
            :disabled="store.isEditing || !instruction.trim()"
            @click="handleEdit"
          >
            {{ store.isEditing ? "调整中…" : "执行调整" }}
          </button>
        </div>
      </div>
      <div class="form-group" style="margin-bottom: 0">
        <label class="form-label">调整指令</label>
        <textarea
          v-model="instruction"
          class="form-textarea"
          rows="2"
          placeholder="例如：第二天轻松一点，不要安排太满，多留点自由时间。"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.smart-editor {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.smart-editor__toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 16px 20px;
  border: none;
  background: none;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.smart-editor__toggle:hover {
  background: var(--color-surface-subtle);
}

.smart-editor__toggle-icon {
  font-size: 12px;
  color: var(--color-text-secondary);
  transition: transform var(--transition-fast);
}

.smart-editor__body {
  padding: 0 20px 20px;
  display: grid;
  gap: 16px;
  border-top: 1px solid var(--color-divider);
}

.smart-editor__row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
</style>
