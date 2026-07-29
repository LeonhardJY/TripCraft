<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

interface MapPoint {
  key: string;
  dayIndex: number;
  date: string;
  theme: string;
  name: string;
  address: string;
  latitude: number | null | undefined;
  longitude: number | null | undefined;
  poiId: string | null | undefined;
  imageUrl?: string | null;
  description: string;
}

const props = defineProps<{ points: MapPoint[] }>();

declare global { interface Window { AMap?: any } }

const mapContainer = ref<HTMLDivElement | null>(null);
const loadError = ref("");
const mapInstance = ref<any>(null);
const overlays = ref<any[]>([]);
const routeLine = ref<any>(null);

const amapKey = import.meta.env.VITE_AMAP_JS_KEY;

const validPoints = computed(() =>
  props.points.filter((p) => p.longitude != null && p.latitude != null)
);

function clearOverlays() {
  if (!mapInstance.value) return;
  overlays.value.forEach((m) => mapInstance.value.remove(m));
  overlays.value = [];
  if (routeLine.value) {
    mapInstance.value.remove(routeLine.value);
    routeLine.value = null;
  }
}

function render() {
  if (!window.AMap || !mapInstance.value) return;
  clearOverlays();

  const sorted = [...validPoints.value].sort((a, b) => a.dayIndex - b.dayIndex);
  const bounds: [number, number][] = [];
  const path: [number, number][] = [];

  sorted.forEach((pt) => {
    const pos: [number, number] = [pt.longitude as number, pt.latitude as number];
    bounds.push(pos);
    path.push(pos);

    const marker = new window.AMap.Marker({
      position: pos,
      offset: new window.AMap.Pixel(-14, -30),
      content: `
        <div style="display:flex;flex-direction:column;align-items:center;">
          <div style="
            width:28px;height:28px;
            display:flex;align-items:center;justify-content:center;
            border-radius:50%;
            background: #C8563C;
            color:#fff;
            font-size:12px;font-weight:700;
            box-shadow:0 2px 8px rgba(200,86,60,0.35);
          ">${pt.dayIndex}</div>
          <div style="
            width:2px;height:6px;
            background:rgba(200,86,60,0.4);
          "></div>
        </div>
      `,
    });

    const info = new window.AMap.InfoWindow({
      offset: new window.AMap.Pixel(0, -36),
      content: `
        <div style="max-width:220px;padding:6px 4px;font-family:-apple-system,sans-serif;line-height:1.6;">
          <strong style="font-size:14px;color:#1C1917;">${pt.name}</strong><br/>
          <span style="font-size:12px;color:#8B8178;">第${pt.dayIndex}天 · ${pt.theme}</span><br/>
          <span style="font-size:12px;color:#8B8178;">${pt.address}</span>
        </div>
      `,
    });

    marker.on("click", () => info.open(mapInstance.value, pos));
    mapInstance.value.add(marker);
    overlays.value.push(marker);
  });

  if (path.length >= 2) {
    routeLine.value = new window.AMap.Polyline({
      path,
      strokeColor: "#C8563C",
      strokeWeight: 2.5,
      strokeOpacity: 0.5,
      strokeStyle: "dashed",
      strokeDasharray: [8, 6],
      lineJoin: "round",
      lineCap: "round",
      showDir: true,
      dirColor: "#C8563C",
      dirSize: 6,
      zIndex: 50,
    });
    mapInstance.value.add(routeLine.value);
  }

  if (bounds.length === 1) {
    mapInstance.value.setZoomAndCenter(13, bounds[0]);
  } else if (bounds.length > 1) {
    mapInstance.value.setFitView(overlays.value, false, [60, 60, 60, 60]);
  }
}

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.AMap) { resolve(); return; }
    const existing = document.querySelector<HTMLScriptElement>('script[data-amap-loader]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("地图脚本加载失败")), { once: true });
      return;
    }
    const s = document.createElement("script");
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${amapKey}`;
    s.async = true;
    s.dataset.amapLoader = "true";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("地图脚本加载失败"));
    document.head.appendChild(s);
  });
}

async function init() {
  if (!amapKey) { loadError.value = "未配置高德地图 Key。"; return; }
  if (!mapContainer.value) return;
  try {
    loadError.value = "";
    await loadScript();
    if (!window.AMap) { loadError.value = "地图初始化失败。"; return; }
    mapInstance.value = new window.AMap.Map(mapContainer.value, {
      zoom: 11,
      resizeEnable: true,
      viewMode: "2D",
      mapStyle: "amap://styles/whitesmoke",
    });
    render();
  } catch {
    loadError.value = "地图加载失败，请检查高德 Key 或网络。";
  }
}

onMounted(() => { void init(); });

watch(validPoints, () => { if (mapInstance.value) render(); });

onBeforeUnmount(() => {
  clearOverlays();
  if (mapInstance.value) {
    mapInstance.value.destroy();
    mapInstance.value = null;
  }
});
</script>

<template>
  <div class="trip-map">
    <div v-if="loadError" class="trip-map__placeholder">
      <span class="trip-map__placeholder-icon">🗺️</span>
      <strong>地图暂不可用</strong>
      <span>{{ loadError }}</span>
    </div>
    <div v-else-if="validPoints.length === 0" class="trip-map__placeholder">
      <span class="trip-map__placeholder-icon">📍</span>
      <strong>暂无景点坐标</strong>
      <span>行程中还没有可标注的坐标信息</span>
    </div>
    <div v-else ref="mapContainer" class="trip-map__canvas" />
  </div>
</template>

<style scoped>
.trip-map {
  min-height: 280px;
  height: 100%;
}

.trip-map__canvas {
  width: 100%;
  height: 100%;
  min-height: 280px;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.trip-map__placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 100%;
  min-height: 200px;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-align: center;
  padding: 32px;
}

.trip-map__placeholder-icon {
  font-size: 32px;
  margin-bottom: 4px;
}

.trip-map__placeholder strong {
  font-family: var(--font-heading);
  font-size: 16px;
  color: var(--color-text-primary);
}

.trip-map__placeholder span:last-child {
  font-size: 13px;
  max-width: 300px;
}
</style>
