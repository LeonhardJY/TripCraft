<script setup lang="ts">
</script>

<template>
  <footer class="footer">
    <div class="footer__inner">
      <div class="footer__brand">
        <span class="footer__logo">TripCraft</span>
        <span class="footer__tagline">智能旅行规划 · 设计开发</span>
      </div>
      <div class="footer__links">
        <a href="https://github.com/LeonhardJY" target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        <span class="footer__dot">·</span>
        <span>LeonhardJY</span>
        <span class="footer__dot">·</span>
        <span class="text-sm text-muted">2026</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  margin-top: var(--spacing-20);
  padding: var(--spacing-8) 0;
  border-top: 1px solid var(--color-border);
}

.footer__inner {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer__brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.footer__logo {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.footer__tagline {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.footer__links {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: 13px;
  color: var(--color-text-secondary);
}

.footer__dot {
  color: var(--color-border);
}

@media (max-width: 640px) {
  .footer__inner {
    flex-direction: column;
    gap: var(--spacing-4);
    text-align: center;
  }
}
</style>
