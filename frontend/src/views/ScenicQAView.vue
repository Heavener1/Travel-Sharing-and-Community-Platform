<script setup>
import { onMounted, reactive, ref } from "vue";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const destinations = ref([]);
const aiProviders = ref({});
const form = reactive({
  destination_name: "",
  question: "",
});
const aiForm = reactive({
  provider: "qwen",
  model: "",
});
const answerText = ref("");
const answerProgress = ref(0);
const answerStatus = ref("");
const answerMeta = ref({
  destination_name: "",
  destination_city: "",
});
const answerLoading = ref(false);

const fetchDestinations = async () => {
  const { data } = await http.get("/travel/destinations/");
  destinations.value = data.results ?? data;
};

const fetchAIProviders = async () => {
  if (!authStore.isAuthenticated) return;
  const { data } = await http.get("/ai/providers/");
  aiProviders.value = data;
  if (data[aiForm.provider] && !aiForm.model) {
    aiForm.model = data[aiForm.provider].default_model;
  }
};

const askQuestion = async () => {
  answerLoading.value = true;
  answerText.value = "";
  answerProgress.value = 0;
  answerStatus.value = "准备检索景点资料...";
  answerMeta.value = { destination_name: "", destination_city: "" };

  try {
    await streamRequest({
      path: "/ai/scenic-qa/stream/",
      body: {
        destination_name: form.destination_name,
        question: form.question,
        provider: aiForm.provider,
        model: aiForm.model || undefined,
      },
      onEvent: (event, data) => {
        if (event === "destination") {
          answerMeta.value = {
            destination_name: data.destination_name || "",
            destination_city: data.destination_city || "",
          };
        }
        if (event === "progress") {
          answerProgress.value = data.progress || 0;
          answerStatus.value = data.message || "";
        }
        if (event === "content") {
          answerText.value = data.content || "";
        }
        if (event === "done") {
          answerText.value = data.content || answerText.value;
          answerProgress.value = 100;
          answerStatus.value = "问答完成";
        }
        if (event === "error") {
          answerStatus.value = data.detail || "景点问答失败";
        }
      },
    });
  } catch (error) {
    answerStatus.value = error.message || "景点问答失败";
  } finally {
    answerLoading.value = false;
  }
};

onMounted(async () => {
  await Promise.all([fetchDestinations(), fetchAIProviders()]);
});
</script>

<template>
  <section class="grid-2">
    <article class="panel">
      <p class="eyebrow">景点智能问答</p>
      <div class="form-grid">
        <select v-model="form.destination_name" class="select">
          <option value="">选择景点</option>
          <option v-for="item in destinations" :key="item.id" :value="item.name">
            {{ item.name }} · {{ item.city }}
          </option>
        </select>
        <input v-model="form.destination_name" class="input" placeholder="也可以直接输入景点名称" />
        <textarea
          v-model="form.question"
          class="textarea"
          placeholder="例如：西湖适合玩几天？有什么推荐路线？预算大概多少？"
        ></textarea>
        <div class="grid-3">
          <select v-model="aiForm.provider" class="select" @change="aiForm.model = aiProviders[aiForm.provider]?.default_model || ''">
            <option value="qwen">千问</option>
            <option value="kimi">Kimi</option>
          </select>
          <select v-model="aiForm.model" class="select">
            <option v-for="item in (aiProviders[aiForm.provider]?.models || [])" :key="item" :value="item">
              {{ item }}
            </option>
          </select>
          <input v-model="aiForm.model" class="input" placeholder="也可以手动输入模型名" />
        </div>
        <button
          class="btn btn-primary"
          :disabled="!authStore.isAuthenticated || answerLoading || !form.destination_name || !form.question"
          @click="askQuestion"
        >
          {{ answerLoading ? "问答中..." : "开始问答" }}
        </button>
        <p class="muted">系统会先检索景点资料，再基于景点信息回答你的问题。</p>
      </div>
    </article>

    <article class="panel">
      <p class="eyebrow">问答结果</p>
      <div class="stream-box">
        <div class="stream-head">
          <strong>生成进度</strong>
          <span>{{ answerProgress }}%</span>
        </div>
        <div class="progress-track">
          <div class="progress-bar" :style="{ width: `${answerProgress}%` }"></div>
        </div>
        <p class="muted">{{ answerStatus || "等待提问" }}</p>
      </div>

      <div v-if="answerMeta.destination_name" class="card" style="margin-top: 14px;">
        <h3>{{ answerMeta.destination_name }}</h3>
        <p class="muted">{{ answerMeta.destination_city }}</p>
      </div>

      <div v-if="answerText" class="card" style="margin-top: 14px;">
        <MarkdownContent :content="answerText" />
      </div>
      <p v-else class="muted" style="margin-top: 14px;">
        提交问题后，这里会实时显示针对景点的智能回答。
      </p>
    </article>
  </section>
</template>
