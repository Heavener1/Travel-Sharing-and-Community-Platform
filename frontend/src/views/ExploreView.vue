<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const keyword = ref("");
const onlyHiddenGem = ref(false);
const loading = ref(false);
const progress = ref(0);
const statusText = ref("");
const uploadModalOpen = ref(false);
const uploadLoading = ref(false);
const uploadError = ref("");
const searchData = ref({
  keyword: "",
  es_results: [],
  db_results: [],
  ai_summary: "",
  ai_provider: "",
  ai_error: "",
  featured_results: [],
});
const uploadForm = reactive({
  name: "",
  province: "",
  city: "",
  summary: "",
  cover: "",
  tags: "",
});

const mergedResults = computed(() => {
  const resultMap = new Map();

  for (const item of searchData.value.es_results) {
    resultMap.set(item.id, { ...item, sourceLabels: ["ES"] });
  }

  for (const item of searchData.value.db_results) {
    const existing = resultMap.get(item.id);
    if (existing) {
      existing.sourceLabels = [...new Set([...existing.sourceLabels, "MySQL"])];
    } else {
      resultMap.set(item.id, { ...item, sourceLabels: ["MySQL"] });
    }
  }

  return Array.from(resultMap.values());
});

const resetUploadForm = () => {
  uploadForm.name = "";
  uploadForm.province = "";
  uploadForm.city = "";
  uploadForm.summary = "";
  uploadForm.cover = "";
  uploadForm.tags = "";
  uploadError.value = "";
};

const fetchSmartResults = async () => {
  loading.value = true;
  progress.value = 0;
  statusText.value = "准备搜索...";
  searchData.value = {
    keyword: keyword.value,
    es_results: [],
    db_results: [],
    ai_summary: "",
    ai_provider: "",
    ai_error: "",
    featured_results: [],
  };
  try {
    await streamRequest({
      path: `/travel/smart-search/stream/?q=${encodeURIComponent(keyword.value || "")}&hidden_gem=${onlyHiddenGem.value ? "true" : "false"}`,
      method: "GET",
      onEvent: (event, data) => {
        if (event === "progress") {
          progress.value = data.progress || 0;
          statusText.value = data.message || "";
        }
        if (event === "featured_results") {
          searchData.value.featured_results = data.items || [];
        }
        if (event === "es_results") {
          searchData.value.es_results = data.items || [];
        }
        if (event === "db_results") {
          searchData.value.db_results = data.items || [];
        }
        if (event === "provider") {
          searchData.value.ai_provider = data.provider || "";
        }
        if (event === "ai_content") {
          searchData.value.ai_summary = data.content || "";
        }
        if (event === "error") {
          searchData.value.ai_error = data.detail || "";
        }
        if (event === "done") {
          progress.value = 100;
          statusText.value = searchData.value.keyword ? "搜索完成" : "已加载热门景点";
        }
      },
    });
  } catch (error) {
    searchData.value.ai_error = error.message || "智能搜索失败";
    statusText.value = "搜索失败";
  } finally {
    loading.value = false;
  }
};

const uploadCover = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const payload = new FormData();
  payload.append("file", file);
  const { data } = await http.post("/travel/upload/", payload, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  uploadForm.cover = data.reference || data.url;
};

const submitDestination = async () => {
  uploadLoading.value = true;
  uploadError.value = "";
  try {
    await http.post("/travel/destinations/", uploadForm);
    uploadModalOpen.value = false;
    resetUploadForm();
    await fetchSmartResults();
  } catch (error) {
    uploadError.value = error?.response?.data?.detail || "上传景点失败，请检查必填信息。";
  } finally {
    uploadLoading.value = false;
  }
};

onMounted(fetchSmartResults);
</script>

<template>
  <section class="panel">
    <div class="grid-3">
      <input v-model="keyword" class="input" placeholder="搜索城市、景点、标签、玩法" @keyup.enter="fetchSmartResults" />
      <label class="card">
        <input v-model="onlyHiddenGem" type="checkbox" />
        只看小众景点
      </label>
      <button class="btn btn-primary" @click="fetchSmartResults">
        {{ loading ? "搜索中..." : "智能搜索" }}
      </button>
    </div>
    <div class="stream-box stream-box-inline" style="margin-top: 14px;">
      <strong>搜索进度</strong>
      <div class="progress-track">
        <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
      </div>
      <span class="muted stream-result">{{ statusText || `${progress}%` }}</span>
    </div>
  </section>

  <section v-if="searchData.keyword" class="panel">
    <p class="eyebrow">AI 智能总结</p>
    <p v-if="searchData.ai_error" class="muted">{{ searchData.ai_error }}</p>
    <div v-if="searchData.ai_summary" class="card" style="margin-top: 14px;">
      <MarkdownContent :content="searchData.ai_summary" />
    </div>
  </section>

  <section v-if="!searchData.keyword" class="panel">
    <div class="split">
      <p class="eyebrow">热门景点</p>
      <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated" @click="uploadModalOpen = true">
        上传景点
      </button>
    </div>
    <div class="list-grid">
      <article v-for="item in searchData.featured_results" :key="item.id" class="card">
        <img v-if="item.cover" :src="item.cover" :alt="item.name" class="cover" />
        <h3>{{ item.name }}</h3>
        <p class="muted">{{ item.city }} · {{ item.province }}</p>
        <p>{{ item.summary }}</p>
        <div class="split">
          <span class="pill">评分 {{ item.average_rating }}</span>
          <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
        </div>
      </article>
    </div>
  </section>

  <section v-else class="panel">
    <p class="eyebrow">综合命中结果</p>
    <div class="form-grid">
      <div v-if="!mergedResults.length" class="card muted">当前没有命中的景点结果。</div>
      <article v-for="item in mergedResults" :key="`merged-${item.id}`" class="card">
        <img v-if="item.cover" :src="item.cover" :alt="item.name" class="cover" />
        <div class="split">
          <div>
            <h3>{{ item.name }}</h3>
            <p class="muted">{{ item.city }} · {{ item.province }}</p>
          </div>
          <div class="tag-row">
            <span v-for="source in item.sourceLabels" :key="source" class="tag">{{ source }}</span>
          </div>
        </div>
        <p>{{ item.summary }}</p>
        <div class="tag-row">
          <span v-for="tag in item.tag_list" :key="tag" class="tag">{{ tag }}</span>
        </div>
        <div class="split">
          <span class="pill">评分 {{ item.average_rating }}</span>
          <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
        </div>
      </article>
    </div>
  </section>

  <div v-if="uploadModalOpen" class="modal-backdrop" @click.self="uploadModalOpen = false">
    <div class="modal-card">
      <div class="split">
        <h3>上传景点</h3>
        <button class="btn btn-secondary" @click="uploadModalOpen = false">关闭</button>
      </div>
      <div class="form-grid">
        <input v-model="uploadForm.name" class="input" placeholder="景点名称" />
        <input v-model="uploadForm.province" class="input" placeholder="省份" />
        <input v-model="uploadForm.city" class="input" placeholder="城市" />
        <textarea v-model="uploadForm.summary" class="textarea" placeholder="景点简介"></textarea>
        <input v-model="uploadForm.tags" class="input" placeholder="标签，可选" />
        <input v-model="uploadForm.cover" class="input" placeholder="封面图片引用，可选" />
        <input class="input" type="file" accept="image/*" @change="uploadCover" />
        <p v-if="uploadError" class="muted">{{ uploadError }}</p>
        <button class="btn btn-primary" :disabled="uploadLoading" @click="submitDestination">
          {{ uploadLoading ? "提交中..." : "提交景点" }}
        </button>
      </div>
    </div>
  </div>
</template>
