import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/main.css";

const app = createApp(App);

// Global scroll-reveal directive
app.directive("reveal", {
  mounted(el: HTMLElement) {
    el.classList.add("v-reveal");
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("v-reveal--visible");
          observer.unobserve(el);
        }
      },
      { threshold: 0.08 }
    );
    observer.observe(el);
  },
});

app.use(createPinia());
app.use(router);
app.mount("#app");
