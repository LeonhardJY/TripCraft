<script setup lang="ts">
import { useRouter, useRoute } from "vue-router";
import { useDarkMode } from "../composables/useDarkMode";

const router = useRouter();
const route = useRoute();
const { isDark, toggle } = useDarkMode();

const links = [
  { name: "home", path: "/", label: "发现" },
  { name: "result", path: "/result", label: "我的行程" },
  { name: "history", path: "/history", label: "足迹" },
] as const;
</script>

<template>
  <header class="header">
    <div class="header__inner">
      <button class="header__brand" @click="router.push('/')">
        <span class="header__mark">✦</span>
        <span class="header__name">TripCraft</span>
      </button>

      <nav class="header__nav">
        <button
          v-for="link in links"
          :key="link.name"
          :class="['header__link', { 'header__link--active': route.name === link.name }]"
          @click="router.push(link.path)"
        >
          {{ link.label }}
        </button>
      </nav>

      <div class="header__right">
        <button
          class="header__theme"
          :title="isDark ? '亮色' : '暗色'"
          @click="toggle"
        >
          {{ isDark ? "☀️" : "🌙" }}
        </button>
        <button
          v-if="route.name !== 'home'"
          class="btn btn--primary btn--sm"
          @click="router.push('/')"
        >
          规划旅程
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: var(--header-height);
  background: rgba(244, 241, 234, 0.92);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  transition: background var(--transition-base);
  border-bottom: 1px solid var(--color-divider);
}

.dark .header {
  background: rgba(28, 25, 23, 0.92);
}

.header__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-6);
}

.header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  color: var(--color-text-primary);
}

.header__mark {
  font-size: 20px;
  color: var(--color-accent);
  line-height: 1;
  transition: transform var(--transition-fast);
}

.header__brand:hover .header__mark {
  transform: rotate(90deg) scale(1.2);
}

.header__name {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
  transition: color var(--transition-fast);
}

.header__brand:hover .header__name {
  color: var(--color-accent);
}

.header__nav {
  display: flex;
  gap: var(--spacing-1);
}

.header__link {
  position: relative;
  padding: 8px 20px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.01em;
}

.header__link:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-subtle);
}

.header__link--active {
  color: var(--color-text-primary);
  font-weight: 600;
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.header__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.header__theme {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  transition: all var(--transition-fast);
  line-height: 1;
}

.header__theme:hover {
  background: var(--color-surface-subtle);
  border-color: var(--color-accent);
}

@media (max-width: 640px) {
  .header__inner { padding: 0 var(--spacing-4); }
  .header__name { font-size: 20px; }
  .header__link { padding: 6px 14px; font-size: 13px; }
}
</style>
