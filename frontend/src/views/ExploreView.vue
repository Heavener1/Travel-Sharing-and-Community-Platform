<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { chinaRegions } from "../data/chinaRegions";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";
import { getFavoriteIds, shareContent, toggleFavoriteId } from "../utils/collection";

const authStore = useAuthStore();
const uiStore = useUiStore();

const keyword = ref("");
const loading = ref(false);
const progress = ref(0);
const statusText = ref("");
const uploadModalOpen = ref(false);
const uploadLoading = ref(false);
const uploadError = ref("");
const initialLoading = ref(true);
const favoriteDestinationIds = ref([]);

const searchFilter = reactive({
  source: "all",
  province: "all",
  sort: "score_desc",
});

const searchData = ref({
  keyword: "",
  es_results: [],
  db_results: [],
  ai_summary: "",
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

const provinceOptions = chinaRegions;
const skeletonCards = Array.from({ length: 4 }, (_, index) => ({ id: index }));
const favoriteStorageKey = "travel_favorite_destinations";

const cityOptions = computed(() => chinaRegions.find((item) => item.province === uploadForm.province)?.cities || []);

watch(
  () => uploadForm.province,
  () => {
    uploadForm.city = "";
  },
);

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

  let items = Array.from(resultMap.values());

  if (searchFilter.source !== "all") {
    items = items.filter((item) => item.sourceLabels.includes(searchFilter.source));
  }

  if (searchFilter.province !== "all") {
    items = items.filter((item) => item.province === searchFilter.province);
  }

  const sorted = [...items];
  if (searchFilter.sort === "score_desc") {
    sorted.sort((a, b) => Number(b.average_rating || b.score || 0) - Number(a.average_rating || a.score || 0));
  }
  if (searchFilter.sort === "score_asc") {
    sorted.sort((a, b) => Number(a.average_rating || a.score || 0) - Number(b.average_rating || b.score || 0));
  }
  if (searchFilter.sort === "name_asc") {
    sorted.sort((a, b) => String(a.name).localeCompare(String(b.name), "zh-CN"));
  }
  if (searchFilter.sort === "latest") {
    sorted.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }
  return sorted;
});

const featuredResults = computed(() => {
  const items = [...searchData.value.featured_results];
  const filtered = items.filter((item) => searchFilter.province === "all" || item.province === searchFilter.province);
  if (searchFilter.sort === "score_asc") {
    filtered.sort((a, b) => Number(a.average_rating || a.score || 0) - Number(b.average_rating || b.score || 0));
  } else if (searchFilter.sort === "latest") {
    filtered.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  } else if (searchFilter.sort === "name_asc") {
    filtered.sort((a, b) => String(a.name).localeCompare(String(b.name), "zh-CN"));
  } else {
    filtered.sort((a, b) => Number(b.average_rating || b.score || 0) - Number(a.average_rating || a.score || 0));
  }
  return filtered;
});

const isFavoriteDestination = (id) => favoriteDestinationIds.value.includes(id);

const toggleFavoriteDestination = (item) => {
  favoriteDestinationIds.value = toggleFavoriteId(favoriteStorageKey, item.id);
  uiStore.pushToast(isFavoriteDestination(item.id) ? `已收藏 ${item.name}` : `已取消收藏 ${item.name}`, "success");
};

const shareDestination = async (item) => {
  await shareContent({
    title: item.name,
    path: `/explore/${item.id}`,
    summary: item.summary,
    onSuccess: () => uiStore.pushToast("景点链接已准备好", "success"),
    onError: () => uiStore.pushToast("分享失败，请稍后再试"),
  });
};

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
  initialLoading.value = !searchData.value.keyword && !keyword.value;
  loading.value = true;
  progress.value = 0;
  statusText.value = "准备搜索...";
  searchData.value = {
    keyword: keyword.value,
    es_results: [],
    db_results: [],
    ai_summary: "",
    ai_error: "",
    featured_results: [],
  };

  try {
    await streamRequest({
      path: `/travel/smart-search/stream/?q=${encodeURIComponent(keyword.value || "")}&hidden_gem=false`,
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
    initialLoading.value = false;
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
  event.target.value = "";
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

onMounted(async () => {
  favoriteDestinationIds.value = getFavoriteIds(favoriteStorageKey);
  await fetchSmartResults();
});
</script>

<template>
  <section class="panel">
    <div class="search-bar-row">
      <input v-model="keyword" class="input" placeholder="搜索城市、景点、标签、玩法" @keyup.enter="fetchSmartResults" />
      <button class="btn btn-primary search-submit-btn" @click="fetchSmartResults">
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
    <div class="split">
      <div>
        <p class="eyebrow">AI 智能总结</p>
        <h3>综合检索与智能推荐结果</h3>
      </div>
      <div class="filter-bar filter-bar-tight">
        <select v-model="searchFilter.source" class="select">
          <option value="all">全部来源</option>
          <option value="ES">仅看 ES</option>
          <option value="MySQL">仅看 MySQL</option>
        </select>
        <select v-model="searchFilter.province" class="select">
          <option value="all">全部省份</option>
          <option v-for="item in provinceOptions" :key="item.province" :value="item.province">{{ item.province }}</option>
        </select>
        <select v-model="searchFilter.sort" class="select">
          <option value="score_desc">评分从高到低</option>
          <option value="score_asc">评分从低到高</option>
          <option value="latest">最新上传优先</option>
          <option value="name_asc">按名称排序</option>
        </select>
      </div>
    </div>

    <p v-if="searchData.ai_error" class="muted">{{ searchData.ai_error }}</p>
    <div v-if="searchData.ai_summary" class="card markdown-wrap" style="margin-top: 14px;">
      <MarkdownContent :content="searchData.ai_summary" />
    </div>

    <div class="form-grid" style="margin-top: 16px;">
      <article v-if="loading" v-for="item in skeletonCards" :key="`result-${item.id}`" class="card skeleton-card">
        <div class="skeleton-media"></div>
        <div class="skeleton-line skeleton-line-title"></div>
        <div class="skeleton-line skeleton-line-subtitle"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-actions">
          <span class="skeleton-chip"></span>
          <span class="skeleton-chip"></span>
          <span class="skeleton-chip"></span>
        </div>
      </article>

      <div v-else-if="!mergedResults.length" class="card empty-state-card">
        <div class="empty-state-illustration scenic-empty-art"></div>
        <h3>没有找到匹配景点</h3>
        <p class="muted">可以换个关键词、调整筛选条件，或者上传一个新的景点内容。</p>
      </div>

      <article v-else v-for="item in mergedResults" :key="`merged-${item.id}`" class="card interactive-card">
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
        <p class="summary-two-lines">{{ item.summary }}</p>
        <div class="tag-row">
          <span v-for="tag in item.tag_list" :key="tag" class="tag">{{ tag }}</span>
        </div>
        <div class="split">
          <span class="pill">评分 {{ item.average_rating }}</span>
          <div class="action-row">
            <button class="btn btn-secondary" @click="toggleFavoriteDestination(item)">
              {{ isFavoriteDestination(item.id) ? "取消收藏" : "收藏" }}
            </button>
            <button class="btn btn-secondary" @click="shareDestination(item)">分享</button>
            <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
          </div>
        </div>
      </article>
    </div>
  </section>

  <section v-else class="panel">
    <div class="split">
      <div>
        <p class="eyebrow">热门景点</p>
        <h3>平台内值得优先浏览的景点内容</h3>
      </div>
      <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated" @click="uploadModalOpen = true">上传景点</button>
    </div>

    <div class="filter-bar" style="margin-top: 16px;">
      <select v-model="searchFilter.province" class="select">
        <option value="all">全部省份</option>
        <option v-for="item in provinceOptions" :key="item.province" :value="item.province">{{ item.province }}</option>
      </select>
      <select v-model="searchFilter.sort" class="select">
        <option value="score_desc">评分从高到低</option>
        <option value="score_asc">评分从低到高</option>
        <option value="latest">最新上传优先</option>
        <option value="name_asc">按名称排序</option>
      </select>
    </div>

    <div class="list-grid" style="margin-top: 16px;">
      <article v-if="initialLoading" v-for="item in skeletonCards" :key="`featured-${item.id}`" class="card skeleton-card">
        <div class="skeleton-media"></div>
        <div class="skeleton-line skeleton-line-title"></div>
        <div class="skeleton-line skeleton-line-subtitle"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-actions">
          <span class="skeleton-chip"></span>
          <span class="skeleton-chip"></span>
        </div>
      </article>

      <div v-else-if="!featuredResults.length" class="card empty-state-card">
        <div class="empty-state-illustration scenic-empty-art"></div>
        <h3>当前筛选下暂无景点</h3>
        <p class="muted">你可以切换省份筛选，或者直接上传一个新的景点资料。</p>
      </div>

      <article v-else v-for="item in featuredResults" :key="item.id" class="card interactive-card">
        <img v-if="item.cover" :src="item.cover" :alt="item.name" class="cover" />
        <h3>{{ item.name }}</h3>
        <p class="muted">{{ item.city }} · {{ item.province }}</p>
        <p class="summary-two-lines">{{ item.summary }}</p>
        <div class="split">
          <span class="pill">评分 {{ item.average_rating }}</span>
          <div class="action-row">
            <button class="btn btn-secondary" @click="toggleFavoriteDestination(item)">
              {{ isFavoriteDestination(item.id) ? "取消收藏" : "收藏" }}
            </button>
            <button class="btn btn-secondary" @click="shareDestination(item)">分享</button>
            <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
          </div>
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
        <select v-model="uploadForm.province" class="select">
          <option value="">选择省份</option>
          <option v-for="item in provinceOptions" :key="item.province" :value="item.province">{{ item.province }}</option>
        </select>
        <select v-model="uploadForm.city" class="select" :disabled="!uploadForm.province">
          <option value="">{{ uploadForm.province ? "选择城市" : "请先选择省份" }}</option>
          <option v-for="city in cityOptions" :key="city" :value="city">{{ city }}</option>
        </select>
        <textarea v-model="uploadForm.summary" class="textarea" placeholder="景点简介"></textarea>
        <input v-model="uploadForm.cover" class="input" placeholder="景点封面引用" />
        <input class="input" type="file" accept="image/*" @change="uploadCover" />
        <input v-model="uploadForm.tags" class="input" placeholder="标签，例如：自然风光,亲子,历史人文" />
        <p v-if="uploadError" class="muted">{{ uploadError }}</p>
        <button class="btn btn-primary" :disabled="uploadLoading" @click="submitDestination">
          {{ uploadLoading ? "上传中..." : "提交景点" }}
        </button>
      </div>
    </div>
  </div>
</template>
