<script setup>
import { onMounted, reactive, ref } from "vue";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const form = reactive({
  departure_city: "上海",
  destination_city: "杭州",
  days: 3,
  budget: 3000,
  preferences: "海岛,摄影,慢旅行",
});
const result = ref(null);
const aiAdvice = ref("");
const aiLoading = ref(false);
const aiProgress = ref(0);
const aiStatus = ref("");
const plannerError = ref("");

const generatePlan = async () => {
  plannerError.value = "";
  result.value = null;
  try {
    const { data } = await http.post("/planner/generate/", form);
    result.value = data;
  } catch (error) {
    plannerError.value = error?.response?.data?.detail || "行程生成失败，请检查出发地和目的地。";
  }
};

const askAI = async () => {
  aiLoading.value = true;
  aiProgress.value = 0;
  aiStatus.value = "准备请求 AI...";
  aiAdvice.value = "";
  try {
    const draft = result.value ? JSON.stringify(result.value.itinerary) : "";
    await streamRequest({
      path: "/ai/travel-assistant/stream/",
      body: {
        ...form,
        draft_itinerary: draft,
      },
      onEvent: (event, data) => {
        if (event === "progress") {
          aiProgress.value = data.progress || 0;
          aiStatus.value = data.message || "";
        }
        if (event === "content") {
          aiAdvice.value = data.content || "";
        }
        if (event === "done") {
          aiAdvice.value = data.content || aiAdvice.value;
          aiProgress.value = 100;
          aiStatus.value = "生成完成";
        }
        if (event === "error") {
          aiStatus.value = data.detail || "AI 生成失败";
        }
      },
    });
  } catch (error) {
    aiStatus.value = error.message || "AI 生成失败";
  } finally {
    aiLoading.value = false;
  }
};

onMounted(() => {});
</script>

<template>
  <section class="grid-2">
    <article class="panel">
      <p class="eyebrow">输入出行信息</p>
      <div class="form-grid">
        <input v-model="form.departure_city" class="input" placeholder="出发地" />
        <input v-model="form.destination_city" class="input" placeholder="目的地" />
        <input v-model="form.days" class="input" type="number" min="1" max="7" placeholder="出行天数" />
        <input v-model="form.budget" class="input" type="number" min="500" placeholder="预算" />
        <input v-model="form.preferences" class="input" placeholder="偏好标签，逗号分隔" />
        <button class="btn btn-primary" :disabled="!authStore.isAuthenticated" @click="generatePlan">
          {{ authStore.isAuthenticated ? "生成我的行程" : "登录后可生成行程" }}
        </button>
        <p v-if="plannerError" class="muted">{{ plannerError }}</p>
      </div>
    </article>

    <article class="panel">
      <p class="eyebrow">规划结果</p>
      <div v-if="result" class="form-grid">
        <div class="card">
          <h3>{{ result.trip.title }}</h3>
          <p class="muted">
            {{ result.trip.departure_city }} 出发 · 前往 {{ result.trip.destination_city }} · 预算 {{ result.trip.budget }} · {{ result.trip.days }} 天
          </p>
        </div>
        <div v-for="(items, day) in result.itinerary" :key="day" class="card">
          <h3>第 {{ day }} 天</h3>
          <div v-for="item in items" :key="item.destination_id">
            <p><strong>{{ item.destination_name }}</strong> · {{ item.city }}</p>
            <p class="muted">{{ item.note }}</p>
          </div>
        </div>
      </div>
      <p v-else class="muted">生成后会展示按天拆分的景点路线建议。</p>
    </article>
  </section>

  <section class="panel">
    <p class="eyebrow">AI 行程顾问</p>
    <div class="action-row">
      <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated || aiLoading" @click="askAI">
        {{ aiLoading ? "生成中..." : "让 AI 优化这份行程" }}
      </button>
    </div>
    <div v-if="aiLoading || aiAdvice || aiStatus" class="stream-box" style="margin-top: 14px;">
      <div class="stream-head">
        <strong>AI 生成进度</strong>
        <span>{{ aiProgress }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-bar" :style="{ width: `${aiProgress}%` }"></div>
      </div>
      <p class="muted">{{ aiStatus }}</p>
      <div v-if="aiAdvice" class="card">
        <MarkdownContent :content="aiAdvice" />
      </div>
    </div>
  </section>
</template>
