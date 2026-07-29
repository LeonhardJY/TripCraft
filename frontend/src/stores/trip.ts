import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "axios";

import {
  generateTrip as apiGenerateTrip,
  editTrip as apiEditTrip,
  saveTrip as apiSaveTrip,
  listTrips as apiListTrips,
  getTripDetail as apiGetTripDetail,
  deleteTrip as apiDeleteTrip,
  fetchWeatherForecast as apiFetchWeather,
} from "../services/api";

import type {
  Itinerary,
  TripEditPayload,
  TripRequestPayload,
  TripSummaryItem,
  WeatherForecastResponse,
} from "../types";

function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (err.code === "ECONNABORTED") return "请求超时，模型返回较慢，请稍后再试。";
    if (err.response) {
      const data = err.response.data;
      if (data && typeof data === "object") {
        if ("detail" in data) {
          const d = data.detail;
          if (typeof d === "string") return d;
          if (d && typeof d === "object" && "message" in d && typeof d.message === "string") return d.message;
        }
        if ("message" in data && typeof data.message === "string") return data.message;
      }
      return `服务端返回 ${err.response.status}，请稍后重试。`;
    }
    return "无法连接服务端，请检查网络或服务状态。";
  }
  if (err instanceof Error) return err.message;
  return "发生未知错误。";
}

export const useTripStore = defineStore("trip", () => {
  // --- State ---
  const currentItinerary = ref<Itinerary | null>(null);
  const weather = ref<WeatherForecastResponse | null>(null);
  const historyList = ref<TripSummaryItem[]>([]);

  const isGenerating = ref(false);
  const isEditing = ref(false);
  const isSaving = ref(false);
  const isExportingPdf = ref(false);
  const isExportingMarkdown = ref(false);
  const isWeatherLoading = ref(false);
  const isHistoryLoading = ref(false);

  const generateError = ref<string | null>(null);
  const weatherError = ref<string | null>(null);
  const historyError = ref<string | null>(null);

  // --- Actions ---
  async function generateTrip(payload: TripRequestPayload) {
    isGenerating.value = true;
    generateError.value = null;
    try {
      const itinerary = await apiGenerateTrip(payload);
      currentItinerary.value = itinerary;
      fetchWeather(itinerary.destination);
      return itinerary;
    } catch (err) {
      const msg = extractError(err);
      generateError.value = msg;
      throw err;
    } finally {
      isGenerating.value = false;
    }
  }

  async function editTrip(instruction: string, dayIndex?: number) {
    if (!currentItinerary.value) return;
    isEditing.value = true;
    try {
      const payload: TripEditPayload = {
        trip_id: currentItinerary.value.trip_id,
        current_itinerary: currentItinerary.value,
        user_instruction: instruction,
        edit_scope: dayIndex ? `day_${dayIndex}` : `day_${currentItinerary.value.days[0]?.day_index ?? 1}`,
        preserve_constraints: ["保留预算结构", "保留目的地和旅行日期"],
      };
      const updated = await apiEditTrip(payload);
      currentItinerary.value = updated;
    } finally {
      isEditing.value = false;
    }
  }

  async function saveCurrentTrip() {
    if (!currentItinerary.value) return;
    isSaving.value = true;
    try {
      await apiSaveTrip(currentItinerary.value);
    } finally {
      isSaving.value = false;
    }
  }

  async function loadHistory() {
    isHistoryLoading.value = true;
    historyError.value = null;
    try {
      const res = await apiListTrips();
      historyList.value = res.items;
    } catch (err) {
      historyError.value = extractError(err);
    } finally {
      isHistoryLoading.value = false;
    }
  }

  async function loadTripDetail(tripId: string) {
    try {
      const res = await apiGetTripDetail(tripId);
      currentItinerary.value = res.itinerary;
      fetchWeather(res.itinerary.destination);
      return res.itinerary;
    } catch (err) {
      throw new Error(extractError(err));
    }
  }

  async function removeTrip(tripId: string) {
    await apiDeleteTrip(tripId);
    historyList.value = historyList.value.filter((t) => t.trip_id !== tripId);
  }

  async function fetchWeather(city: string) {
    isWeatherLoading.value = true;
    weatherError.value = null;
    try {
      weather.value = await apiFetchWeather(city);
    } catch {
      weatherError.value = "天气信息暂时不可用。";
      weather.value = null;
    } finally {
      isWeatherLoading.value = false;
    }
  }

  function setItinerary(itinerary: Itinerary) {
    currentItinerary.value = itinerary;
  }

  function clearError() {
    generateError.value = null;
  }

  return {
    currentItinerary,
    weather,
    historyList,
    isGenerating,
    isEditing,
    isSaving,
    isExportingPdf,
    isExportingMarkdown,
    isWeatherLoading,
    isHistoryLoading,
    generateError,
    weatherError,
    historyError,
    generateTrip,
    editTrip,
    saveCurrentTrip,
    loadHistory,
    loadTripDetail,
    removeTrip,
    fetchWeather,
    setItinerary,
    clearError,
  };
});
