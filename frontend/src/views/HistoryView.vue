<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useTripStore } from "../stores/trip";

const store = useTripStore();
const router = useRouter();

const loadingId = ref<string | null>(null);
const deletingId = ref<string | null>(null);

onMounted(() => { store.loadHistory(); });

const totalDestinations = computed(() => {
  const set = new Set(store.historyList.map((t) => t.destination));
  return set.size;
});

const totalTrips = computed(() => store.historyList.length);

async function openTrip(tripId: string) {
  loadingId.value = tripId;
  try {
    await store.loadTripDetail(tripId);
    router.push({ name: "result" });
  } finally { loadingId.value = null; }
}

async function removeTrip(tripId: string) {
  if (!confirm("确定删除这条行程？删除后无法恢复。")) return;
  deletingId.value = tripId;
  try {
    await store.removeTrip(tripId);
  } finally { deletingId.value = null; }
}

function formatDate(d?: string | null) {
  if (!d) return "";
  const date = new Date(d);
  const months = ["一月", "二月", "三月", "四月", "五月", "六月",
                  "七月", "八月", "九月", "十月", "十一月", "十二月"];
  return `${date.getFullYear()}年 ${months[date.getMonth()]}`;
}
</script>

<template>
  <div class="history">
    <div class="section">
      <!-- Hero -->
      <div class="history-hero" v-reveal>
        <p class="history-hero__eyebrow">Journal · 足迹</p>
        <h1 class="history-hero__title">旅行笔记</h1>
        <p class="history-hero__subtitle">
          每一次出发，都值得被记录。已保存的全部旅行方案。
        </p>
      </div>

      <!-- Stats (only when data exists) -->
      <div v-if="store.historyList.length > 0" class="history-stats" v-reveal>
        <div class="history-stats__item">
          <span class="history-stats__num">{{ totalTrips }}</span>
          <span class="history-stats__label">总行程</span>
        </div>
        <div class="history-stats__item">
          <span class="history-stats__num">{{ totalDestinations }}</span>
          <span class="history-stats__label">到访城市</span>
        </div>
        <div class="history-stats__item">
          <button class="btn btn--sm" :disabled="store.isHistoryLoading" @click="store.loadHistory()">
            {{ store.isHistoryLoading ? "刷新中…" : "↻ 刷新" }}
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="store.isHistoryLoading" class="history-loading">
        <div class="timeline">
          <div v-for="i in 3" :key="i" class="timeline-item">
            <div class="timeline-item__dot" style="background: var(--color-border)"></div>
            <div class="timeline-item__content" style="padding: 20px">
              <div class="skeleton skeleton--title" />
              <div class="skeleton skeleton--text" style="width: 70%" />
              <div class="skeleton skeleton--text" style="width: 50%" />
            </div>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="store.historyError" class="history-empty">
        <div class="card" style="text-align: center; padding: var(--spacing-10)">
          <p class="text-muted" style="margin-bottom: var(--spacing-4)">
            {{ store.historyError }}
          </p>
          <button class="btn btn--sm" @click="store.loadHistory()">重试</button>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="store.historyList.length === 0" class="history-empty" v-reveal>
        <div class="history-empty__inner">
          <div class="history-empty__icon">✈️</div>
          <h2>还没有保存的行程</h2>
          <p class="text-muted" style="margin-bottom: var(--spacing-6); max-width: 360px; margin-left: auto; margin-right: auto;">
            当你生成并保存一条旅行方案后，它会作为一篇旅行笔记出现在这里。
          </p>
          <button class="btn btn--primary" @click="router.push({ name: 'home' })">
            开始规划旅程
          </button>
        </div>
      </div>

      <!-- Timeline List -->
      <div v-else class="timeline-wrap" v-reveal>
        <div class="timeline">
          <div
            v-for="(item, index) in store.historyList"
            :key="item.trip_id"
            class="timeline-item"
            v-reveal
          >
            <div class="timeline-item__dot" />
            <div class="timeline-item__content">
              <div class="timeline-item__header">
                <div class="timeline-item__index">#{{ index + 1 }}</div>
                <h3 class="timeline-item__title">{{ item.destination }}</h3>
                <span class="timeline-item__date">{{ formatDate(item.updated_at || item.created_at) }}</span>
              </div>
              <p class="timeline-item__summary">{{ item.summary }}</p>
              <div class="timeline-item__actions">
                <button
                  class="btn btn--primary btn--sm"
                  :disabled="loadingId === item.trip_id"
                  @click="openTrip(item.trip_id)"
                >
                  {{ loadingId === item.trip_id ? "载入中…" : "阅读笔记" }}
                </button>
                <button
                  class="btn btn--ghost btn--sm"
                  :disabled="deletingId === item.trip_id"
                  @click="removeTrip(item.trip_id)"
                >
                  {{ deletingId === item.trip_id ? "删除中…" : "删除" }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history {
  padding: var(--spacing-10) 0 var(--spacing-16);
}

/* Hero */
.history-hero {
  margin-bottom: var(--spacing-8);
}

.history-hero__eyebrow {
  font-family: var(--font-display);
  font-size: 15px;
  font-style: italic;
  color: var(--color-accent);
  margin-bottom: var(--spacing-2);
}

.history-hero__title {
  font-size: 38px;
  margin-bottom: var(--spacing-2);
}

.history-hero__subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  max-width: 480px;
}

/* Stats */
.history-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-10);
  margin-bottom: var(--spacing-10);
  padding: var(--spacing-5) var(--spacing-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.history-stats__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.history-stats__num {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
}

.history-stats__label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* Loading */
.history-loading {
  max-width: 620px;
}

/* Empty */
.history-empty {
  max-width: 520px;
  margin: 0 auto;
}

.history-empty__inner {
  text-align: center;
  padding: var(--spacing-16) 0;
}

.history-empty__icon {
  font-size: 56px;
  margin-bottom: var(--spacing-5);
}

.history-empty__inner h2 {
  margin-bottom: var(--spacing-2);
}

/* Timeline */
.timeline-wrap {
  max-width: 680px;
  margin: 0 auto;
}

.timeline-item__header {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.timeline-item__index {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
  color: var(--color-accent);
  opacity: 0.6;
  min-width: 28px;
}

.timeline-item__title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  flex: 1;
}

.timeline-item__date {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.timeline-item__summary {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: var(--spacing-2) 0 var(--spacing-4);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.timeline-item__actions {
  display: flex;
  gap: var(--spacing-2);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--color-divider);
}

@media (max-width: 640px) {
  .history-hero__title { font-size: 30px; }
  .history-stats { flex-direction: column; align-items: flex-start; gap: var(--spacing-4); }
  .timeline-item__header { flex-wrap: wrap; }
  .timeline-item__date { width: 100%; padding-left: 28px; }
}
</style>
