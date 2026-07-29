import { createRouter, createWebHistory } from "vue-router";
import { useTripStore } from "../stores/trip";

const HomeView = () => import("../views/HomeView.vue");
const ResultView = () => import("../views/ResultView.vue");
const HistoryView = () => import("../views/HistoryView.vue");

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/result",
      name: "result",
      component: ResultView,
      beforeEnter: (_to, _from, next) => {
        const store = useTripStore();
        if (!store.currentItinerary) {
          next({ name: "home" });
        } else {
          next();
        }
      },
    },
    {
      path: "/history",
      name: "history",
      component: HistoryView,
    },
  ],
});

export default router;
