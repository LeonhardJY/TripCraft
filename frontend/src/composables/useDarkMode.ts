import { ref, watch } from "vue";

const isDark = ref(false);
const KEY = "tripcraft-theme";

function apply(val: boolean) {
  document.documentElement.classList.toggle("dark", val);
  isDark.value = val;
}

export function useDarkMode() {
  const stored = localStorage.getItem(KEY);
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  apply(stored !== null ? stored === "dark" : prefersDark);

  watch(isDark, (val) => {
    localStorage.setItem(KEY, val ? "dark" : "light");
  });

  function toggle() {
    apply(!isDark.value);
  }

  return { isDark, toggle };
}
