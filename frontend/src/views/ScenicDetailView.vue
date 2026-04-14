<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import MarkdownContent from "../components/MarkdownContent.vue";
import { useReadingProgress } from "../composables/useReadingProgress";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();
const { readingProgress } = useReadingProgress();

const destination = ref(null);
const loading = ref(false);
const submitLoading = ref(false);
const reviewError = ref("");
const allRelatedDestinations = ref([]);
const allRelatedPosts = ref([]);
const relatedBatchIndex = ref(0);
const relatedLoading = ref(false);
const reviewForm = reactive({
  rating: 5,
  content: "",
});
const analysisLoading = ref(false);
const analysisProgress = ref(0);
const analysisStatus = ref("");
const analysisText = ref("");

const maxRatingCount = computed(() => {
  if (!destination.value?.rating_distribution?.length) return 1;
  return Math.max(...destination.value.rating_distribution.map((item) => item.count), 1);
});

const relatedDestinations = computed(() => {
  const list = allRelatedDestinations.value;
  if (!list.length) return [];
  const start = (relatedBatchIndex.value * 4) % list.length;
  return Array.from({ length: Math.min(4, list.length) }, (_, index) => list[(start + index) % list.length]);
});

const relatedPosts = computed(() => {
  const list = allRelatedPosts.value;
  if (!list.length) return [];
  const start = (relatedBatchIndex.value * 4) % list.length;
  return Array.from({ length: Math.min(4, list.length) }, (_, index) => list[(start + index) % list.length]);
});

const nextRelatedBatch = () => {
  relatedBatchIndex.value += 1;
};

const fetchRelatedContent = async (destinationId) => {
  relatedLoading.value = true;
  try {
    const { data } = await http.get(`/travel/destinations/${destinationId}/related/`);
    allRelatedDestinations.value = data.related_destinations || [];
    allRelatedPosts.value = data.related_posts || [];
    relatedBatchIndex.value = 0;
  } finally {
    relatedLoading.value = false;
  }
};

const fetchDestination = async () => {
  loading.value = true;
  try {
    const { data } = await http.get(`/travel/destinations/${route.params.id}/`);
    destination.value = data;
    await fetchRelatedContent(data.id);
  } finally {
    loading.value = false;
  }
};

const scrollToSection = (id) => {
  const element = document.getElementById(id);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

const backToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const submitReview = async () => {
  if (!destination.value) return;
  submitLoading.value = true;
  reviewError.value = "";
  try {
    const { data } = await http.post(`/travel/destinations/${destination.value.id}/reviews/`, reviewForm);
    destination.value = data;
    reviewForm.content = "";
    await fetchRelatedContent(data.id);
  } catch (error) {
    reviewError.value = error?.response?.data?.detail || "提交评价失败，请检查评分或稍后再试。";
  } finally {
    submitLoading.value = false;
  }
};

const runAnalysis = async () => {
  if (!destination.value) return;
  analysisLoading.value = true;
  analysisProgress.value = 0;
  analysisStatus.value = "正在整理景点评价与评分数据...";
  analysisText.value = "";
  try {
    await streamRequest({
      path: "/ai/destination-analysis/stream/",
      body: { destination_id: destination.value.id },
      onEvent: (event, data) => {
        if (event === "progress") {
          analysisProgress.value = data.progress || 0;
          analysisStatus.value = data.message || "";
        }
        if (event === "content") {
          analysisText.value = data.content || "";
        }
        if (event === "done") {
          analysisText.value = data.content || analysisText.value;
          analysisProgress.value = 100;
          analysisStatus.value = "分析完成";
        }
        if (event === "error") {
          analysisStatus.value = data.detail || "AI 分析失败";
        }
      },
    });
  } catch (error) {
    analysisStatus.value = error.message || "AI 分析失败";
  } finally {
    analysisLoading.value = false;
  }
};

onMounted(fetchDestination);

watch(
  () => route.params.id,
  async () => {
    await fetchDestination();
  },
);
</script>

<template>
  <section v-if="destination" class="page detail-page">
    <div class="reading-progress">
      <div class="reading-progress-bar" :style="{ width: `${readingProgress}%` }"></div>
    </div>

    <div class="detail-sticky-bar">
      <div class="filter-bar filter-bar-tight">
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('scenic-overview')">景点概览</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('scenic-analysis')">评分分析</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('scenic-related')">相关推荐</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('scenic-reviews')">用户评价</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('scenic-review-form')">我要评价</button>
        <button class="btn theme-toggle-btn btn-compact" @click="backToTop">返回顶部</button>
      </div>
    </div>

    <section id="scenic-overview" class="grid-2">
      <article class="panel">
        <img v-if="destination.cover" :src="destination.cover" :alt="destination.name" class="cover detail-cover" />
        <p class="eyebrow">景点详情</p>
        <h2>{{ destination.name }}</h2>
        <p class="muted">{{ destination.city }} · {{ destination.province }}</p>
        <p>{{ destination.summary }}</p>
        <div class="tag-row">
          <span v-for="tag in destination.tag_list" :key="tag" class="tag">{{ tag }}</span>
        </div>

        <div class="stats" style="margin-top: 18px;">
          <div class="card">
            <div class="metric">{{ destination.average_rating }}</div>
            <p class="muted">平均评分</p>
          </div>
          <div class="card">
            <div class="metric">{{ destination.review_count }}</div>
            <p class="muted">评价数量</p>
          </div>
          <div class="card">
            <div class="metric">{{ destination.suggested_days }}</div>
            <p class="muted">建议游玩天数</p>
          </div>
        </div>
      </article>

      <article id="scenic-analysis" class="panel">
        <p class="eyebrow">评分统计</p>
        <div class="form-grid">
          <div v-for="item in destination.rating_distribution" :key="item.star" class="rating-bar-row">
            <span>{{ item.star }} 星</span>
            <div class="progress-track">
              <div class="progress-bar" :style="{ width: `${(item.count / maxRatingCount) * 100}%` }"></div>
            </div>
            <span class="muted">{{ item.count }} 条</span>
          </div>
        </div>

        <div class="form-grid" style="margin-top: 18px;">
          <div class="split">
            <p class="eyebrow">AI 分析</p>
            <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated || analysisLoading" @click="runAnalysis">
              {{ analysisLoading ? "分析中..." : "AI 分析当前景点" }}
            </button>
          </div>
          <div v-if="analysisLoading || analysisText || analysisStatus" class="stream-box">
            <div class="stream-head">
              <strong>分析进度</strong>
              <span>{{ analysisProgress }}%</span>
            </div>
            <div class="progress-track">
              <div class="progress-bar" :style="{ width: `${analysisProgress}%` }"></div>
            </div>
            <p class="muted">{{ analysisStatus }}</p>
            <div v-if="analysisText" class="card markdown-wrap">
              <MarkdownContent :content="analysisText" />
            </div>
          </div>
        </div>
      </article>
    </section>

    <article id="scenic-related" class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">相关推荐</p>
          <h3>和这个景点相关的内容继续看</h3>
        </div>
        <button class="btn btn-secondary btn-compact" :disabled="!allRelatedDestinations.length && !allRelatedPosts.length" @click="nextRelatedBatch">
          换一批
        </button>
      </div>
      <section class="grid-2 related-grid" style="margin-top: 16px;">
        <div class="card">
          <p class="eyebrow">相似景点</p>
          <div v-if="relatedLoading" class="muted">正在整理相关推荐...</div>
          <div v-else-if="!relatedDestinations.length" class="muted">暂时还没有匹配到相似景点。</div>
          <div v-else class="form-grid">
            <RouterLink v-for="item in relatedDestinations" :key="item.id" :to="`/explore/${item.id}`" class="card related-link-card">
              <strong>{{ item.name }}</strong>
              <p class="muted">{{ item.city }} · {{ item.province }}</p>
            </RouterLink>
          </div>
        </div>

        <div class="card">
          <p class="eyebrow">相关帖子</p>
          <div v-if="relatedLoading" class="muted">正在整理相关推荐...</div>
          <div v-else-if="!relatedPosts.length" class="muted">暂时还没有关联的旅行故事。</div>
          <div v-else class="form-grid">
            <RouterLink v-for="item in relatedPosts" :key="item.id" :to="`/community/${item.id}`" class="card related-link-card">
              <strong>{{ item.title }}</strong>
              <p class="muted">{{ item.author_name }} · {{ item.destination_name || "未关联景点" }}</p>
            </RouterLink>
          </div>
        </div>
      </section>
    </article>

    <section class="grid-2">
      <article id="scenic-reviews" class="panel">
        <p class="eyebrow">用户评价</p>
        <div class="form-grid">
          <div v-if="!destination?.reviews?.length" class="card empty-state-card">
            <div class="empty-state-illustration review-empty-art"></div>
            <h3>还没有用户评价</h3>
            <p class="muted">欢迎成为第一位给这个景点留下评分和体验感受的用户。</p>
          </div>
          <div v-for="review in destination?.reviews || []" :key="review.id" class="card">
            <div class="post-author">
              <div class="profile-chip profile-chip-rich">
                <img v-if="review.author_avatar" :src="review.author_avatar" alt="avatar" class="mini-avatar" />
                <span>{{ review.display_name || review.nickname || review.username }}</span>
              </div>
              <span class="pill">{{ review.rating }} 星</span>
            </div>
            <p>{{ review.content || "这位用户只进行了评分，没有填写评价内容。" }}</p>
            <p class="muted">{{ review.created_at }}</p>
          </div>
        </div>
      </article>

      <article id="scenic-review-form" class="panel">
        <p class="eyebrow">我要评价</p>
        <div v-if="destination?.current_user_review" class="card">
          <h3>你已经评价过这个景点了</h3>
          <p class="muted">评分：{{ destination.current_user_review.rating }} 星</p>
          <p>{{ destination.current_user_review.content || "你提交的是仅评分评价。" }}</p>
        </div>
        <div v-else class="form-grid">
          <select v-model="reviewForm.rating" class="select">
            <option :value="5">5 星</option>
            <option :value="4">4 星</option>
            <option :value="3">3 星</option>
            <option :value="2">2 星</option>
            <option :value="1">1 星</option>
          </select>
          <textarea
            v-model="reviewForm.content"
            class="textarea"
            placeholder="可以只打分不写评价；如果填写评价内容，系统会和评分一起提交。"
          ></textarea>
          <p v-if="reviewError" class="muted">{{ reviewError }}</p>
          <button class="btn btn-primary" :disabled="!authStore.isAuthenticated || submitLoading" @click="submitReview">
            {{ submitLoading ? "提交中..." : "提交评分与评价" }}
          </button>
          <p class="muted">每个用户对同一个景点只能评价一次。</p>
        </div>
      </article>
    </section>
  </section>

  <section v-if="loading" class="page">
    <article class="panel skeleton-card">
      <div class="skeleton-media skeleton-media-large"></div>
      <div class="skeleton-line skeleton-line-title"></div>
      <div class="skeleton-line skeleton-line-subtitle"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line skeleton-line-short"></div>
    </article>
  </section>
</template>
