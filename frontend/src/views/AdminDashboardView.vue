<script setup>
import { computed, onMounted, ref } from "vue";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const loading = ref(false);
const dashboard = ref({
  user_count: 0,
  post_count: 0,
  destination_count: 0,
  comment_count: 0,
  review_count: 0,
  pending_post_count: 0,
  pending_comment_count: 0,
  timeline: [],
});

const maxTimelineCount = computed(() => {
  const allCounts = dashboard.value.timeline.flatMap((item) => item.segments.map((segment) => segment.count));
  return Math.max(...allCounts, 1);
});

const fetchDashboard = async () => {
  loading.value = true;
  try {
    const { data } = await http.get("/social/admin/dashboard/");
    dashboard.value = data;
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (authStore.user?.is_staff) {
    fetchDashboard();
  }
});
</script>

<template>
  <section v-if="authStore.user?.is_staff" class="page">
    <section class="grid-3">
      <article class="card">
        <div class="metric">{{ dashboard.user_count }}</div>
        <p class="muted">用户数量</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.post_count }}</div>
        <p class="muted">帖子数量</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.destination_count }}</div>
        <p class="muted">景点数量</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.comment_count }}</div>
        <p class="muted">评论数量</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.review_count }}</div>
        <p class="muted">景点评价数量</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.pending_post_count + dashboard.pending_comment_count }}</div>
        <p class="muted">待审核内容</p>
      </article>
    </section>

    <section class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">发帖时段统计</p>
          <h3>按日期与 6 小时时段查看用户发帖数量</h3>
        </div>
        <p class="muted">{{ loading ? "数据加载中..." : `共 ${dashboard.timeline.length} 天数据` }}</p>
      </div>

      <div class="form-grid" style="margin-top: 18px;">
        <div v-if="!dashboard.timeline.length" class="card muted">当前暂无帖子统计数据。</div>
        <article v-for="item in dashboard.timeline" :key="item.date" class="card">
          <div class="split">
            <div>
              <h3>{{ item.date }}</h3>
              <p class="muted">当日发帖总数 {{ item.total }}</p>
            </div>
          </div>
          <div class="form-grid">
            <div v-for="segment in item.segments" :key="segment.label" class="rating-bar-row">
              <span>{{ segment.label }}</span>
              <div class="progress-track admin-track">
                <div
                  class="progress-bar admin-bar"
                  :style="{ width: `${(segment.count / maxTimelineCount) * 100}%` }"
                ></div>
              </div>
              <span class="muted">{{ segment.count }} 条</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  </section>

  <section v-else class="panel">
    <p class="eyebrow">管理后台</p>
    <h3>当前账号没有管理员权限</h3>
    <p class="muted">请使用管理员账号登录后查看后台统计数据。</p>
  </section>
</template>
