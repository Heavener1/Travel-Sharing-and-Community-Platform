<script setup>
import { onMounted, ref } from "vue";

import http from "../api/http";

const dashboard = ref({
  destination_count: 0,
  hidden_gem_count: 0,
  hotel_count: 0,
  featured_destinations: [],
});
const recommendations = ref([]);

onMounted(async () => {
  const [{ data: dashboardData }, { data: recommendationData }] = await Promise.all([
    http.get("/travel/dashboard/"),
    http.get("/travel/recommendations/"),
  ]);
  dashboard.value = dashboardData;
  recommendations.value = recommendationData;
});
</script>

<template>
  <section class="hero">
    <article class="panel">
      <p class="eyebrow">一站式旅游毕设系统</p>
      <h3>从景点检索、社区分享到行程生成，围绕开题报告落成完整演示闭环。</h3>
      <p class="muted">
        项目基于 Django REST Framework + Vue 3，覆盖旅游信息整合、用户内容共创、行为驱动推荐和轻量智能规划。
      </p>
      <div class="action-row">
        <RouterLink to="/explore" class="btn btn-primary">开始探索</RouterLink>
        <RouterLink to="/planner" class="btn btn-secondary">生成行程</RouterLink>
      </div>
    </article>

    <article class="feature">
      <div class="stats">
        <div>
          <div class="metric">{{ dashboard.destination_count }}</div>
          <p class="muted">景点</p>
        </div>
        <div>
          <div class="metric">{{ dashboard.hidden_gem_count }}</div>
          <p class="muted">小众灵感</p>
        </div>
        <div>
          <div class="metric">{{ dashboard.hotel_count }}</div>
          <p class="muted">住宿方案</p>
        </div>
      </div>
    </article>
  </section>

  <section class="grid-2">
    <article class="panel">
      <p class="eyebrow">精选景点</p>
      <div class="list-grid">
        <div v-for="item in dashboard.featured_destinations" :key="item.id" class="card">
          <img v-if="item.cover" :src="item.cover" :alt="item.name" class="cover" />
          <h3>{{ item.name }}</h3>
          <p class="muted">{{ item.city }} · {{ item.province }}</p>
          <div class="tag-row">
            <span v-for="tag in item.tag_list" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
        </div>
      </div>
    </article>

    <article class="panel">
      <p class="eyebrow">推荐灵感</p>
      <div class="form-grid">
        <div v-for="item in recommendations" :key="item.id" class="card">
          <div class="split">
            <div>
              <h3>{{ item.name }}</h3>
              <p class="muted summary-two-lines">{{ item.summary }}</p>
            </div>
            <span class="pill">评分 {{ item.average_rating || item.score }}</span>
          </div>
          <RouterLink :to="`/explore/${item.id}`" class="btn btn-secondary">查看详情</RouterLink>
        </div>
      </div>
    </article>
  </section>
</template>
