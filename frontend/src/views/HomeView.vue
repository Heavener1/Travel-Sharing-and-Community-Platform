<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import http from "../api/http";
import { fetchFavoriteDestinationIds, toggleDestinationFavorite } from "../api/favorites";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";
import { shareContent } from "../utils/collection";

const authStore = useAuthStore();
const uiStore = useUiStore();

const favoriteDestinationIds = ref([]);
const dashboard = ref({
  destination_count: 0,
  hidden_gem_count: 0,
  hotel_count: 0,
  featured_destinations: [],
});
const recommendations = ref([]);
const loading = ref(true);
const loadError = ref("");
const skeletonCards = Array.from({ length: 3 }, (_, index) => ({ id: index }));

const recommendationCards = computed(() => recommendations.value || []);
const isFavoriteDestination = (id) => favoriteDestinationIds.value.includes(id);

const syncFavoriteIds = async () => {
  favoriteDestinationIds.value = await fetchFavoriteDestinationIds(authStore.isAuthenticated);
};

const toggleFavorite = async (item) => {
  const { favorited, ids } = await toggleDestinationFavorite(item.id, authStore.isAuthenticated);
  favoriteDestinationIds.value = ids;
  uiStore.pushToast(favorited ? `已收藏 ${item.name}` : `已取消收藏 ${item.name}`, "success");
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

const fetchHomeData = async () => {
  loading.value = true;
  loadError.value = "";
  const [dashboardResult, recommendationResult] = await Promise.allSettled([http.get("/travel/dashboard/"), http.get("/travel/recommendations/")]);

  if (dashboardResult.status === "fulfilled") {
    dashboard.value = dashboardResult.value.data;
  }
  if (recommendationResult.status === "fulfilled") {
    recommendations.value = recommendationResult.value.data;
  }
  if (dashboardResult.status === "rejected" && recommendationResult.status === "rejected") {
    loadError.value = "首页数据加载较慢，稍后刷新后会恢复展示。";
  }
  loading.value = false;
};

watch(
  () => authStore.isAuthenticated,
  () => {
    syncFavoriteIds();
  },
);

onMounted(async () => {
  await Promise.all([syncFavoriteIds(), fetchHomeData()]);
});
</script>

<template>
  <section class="hero hero-rich">
    <article class="panel hero-copy">
      <p class="eyebrow">一站式旅游毕业设计系统</p>
      <h3>把景点探索、社区互动、智能搜索和 AI 行程建议整合成一个更完整的旅游平台。</h3>
      <p class="muted">
        项目基于 Django REST Framework 与 Vue 3 构建，结合 ElasticSearch、Redis、MinIO 与大模型能力，
        既能完成基础旅游信息展示，也能提供更智能的问答、总结与规划体验。
      </p>
      <div class="action-row">
        <RouterLink to="/explore" class="btn btn-primary">开始探索</RouterLink>
        <RouterLink to="/planner" class="btn btn-secondary">生成行程</RouterLink>
      </div>
    </article>

    <article class="feature hero-metrics">
      <div class="stats">
        <div>
          <div class="metric">{{ dashboard.destination_count }}</div>
          <p class="muted">景点数据</p>
        </div>
        <div>
          <div class="metric">{{ dashboard.hidden_gem_count }}</div>
          <p class="muted">特色推荐</p>
        </div>
        <div>
          <div class="metric">{{ dashboard.hotel_count }}</div>
          <p class="muted">住宿方案</p>
        </div>
      </div>
      <div class="hero-note">
        <p class="muted">支持图文社区、景点评价、AI 问答、流式智能搜索与消息通知。</p>
      </div>
    </article>
  </section>

  <section v-if="loadError" class="panel">
    <p class="muted">{{ loadError }}</p>
  </section>

  <section class="grid-2">
    <article class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">精选景点</p>
          <h3>适合首页展示的热门内容</h3>
        </div>
        <span class="pill">{{ loading ? "加载中" : `${dashboard.featured_destinations.length} 个` }}</span>
      </div>
      <div class="list-grid">
        <div v-if="loading" v-for="item in skeletonCards" :key="`featured-${item.id}`" class="card skeleton-card">
          <div class="skeleton-media"></div>
          <div class="skeleton-line skeleton-line-title"></div>
          <div class="skeleton-line skeleton-line-subtitle"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-actions">
            <span class="skeleton-chip"></span>
            <span class="skeleton-chip"></span>
          </div>
        </div>
        <div v-else v-for="item in dashboard.featured_destinations" :key="item.id" class="card interactive-card">
          <img v-if="item.cover" :src="item.cover" :alt="item.name" class="cover" />
          <h3>{{ item.name }}</h3>
          <p class="muted">{{ item.city }} · {{ item.province }}</p>
          <p class="summary-two-lines">{{ item.summary }}</p>
          <div class="tag-row">
            <span v-for="tag in item.tag_list" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <div class="action-row card-action-row">
            <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
            <button class="btn btn-secondary" @click="toggleFavorite(item)">
              {{ isFavoriteDestination(item.id) ? "取消收藏" : "收藏" }}
            </button>
            <button class="btn btn-secondary" @click="shareDestination(item)">分享</button>
          </div>
        </div>
      </div>
    </article>

    <article class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">推荐灵感</p>
          <h3>基于用户行为和平台内容生成的出游方向</h3>
        </div>
        <span class="pill">{{ loading ? "加载中" : `${recommendationCards.length} 条` }}</span>
      </div>
      <div class="form-grid">
        <div v-if="loading" v-for="item in skeletonCards" :key="`recommend-${item.id}`" class="card skeleton-card">
          <div class="skeleton-line skeleton-line-title"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line skeleton-line-short"></div>
          <div class="skeleton-actions">
            <span class="skeleton-chip"></span>
          </div>
        </div>
        <div v-else v-for="item in recommendationCards" :key="item.id" class="card interactive-card">
          <div class="split">
            <div>
              <h3>{{ item.name }}</h3>
              <p class="muted summary-two-lines">{{ item.summary }}</p>
            </div>
            <span class="pill">评分 {{ item.average_rating || item.score }}</span>
          </div>
          <div class="action-row card-action-row">
            <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
            <button class="btn btn-secondary" @click="toggleFavorite(item)">
              {{ isFavoriteDestination(item.id) ? "取消收藏" : "收藏" }}
            </button>
            <button class="btn btn-secondary" @click="shareDestination(item)">分享</button>
          </div>
        </div>
      </div>
    </article>
  </section>
</template>
