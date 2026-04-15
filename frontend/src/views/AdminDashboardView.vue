<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";

const authStore = useAuthStore();
const uiStore = useUiStore();

const loading = ref(false);
const actionLoading = ref("");
const batchResult = ref(null);
const dashboard = ref({
  user_count: 0,
  post_count: 0,
  destination_count: 0,
  comment_count: 0,
  review_count: 0,
  pending_post_count: 0,
  pending_comment_count: 0,
  timeline: [],
  recent_trends: [],
});

const batchForms = reactive({
  accounts: {
    count: 20,
    start_number: 1000,
  },
  destinations: {
    count: 15,
  },
  posts: {
    count: 30,
  },
});

const maxTimelineCount = computed(() => {
  const allCounts = dashboard.value.timeline.flatMap((item) => item.segments.map((segment) => segment.count));
  return Math.max(...allCounts, 1);
});

const maxTrendCount = computed(() => {
  const allCounts = dashboard.value.recent_trends.flatMap((item) => [item.user_count, item.post_count, item.destination_count]);
  return Math.max(...allCounts, 1);
});

const statCards = computed(() => [
  { label: "用户数量", value: dashboard.value.user_count },
  { label: "帖子数量", value: dashboard.value.post_count },
  { label: "景点数量", value: dashboard.value.destination_count },
  { label: "评论数量", value: dashboard.value.comment_count },
  { label: "景点评价数量", value: dashboard.value.review_count },
  { label: "待处理内容", value: dashboard.value.pending_post_count + dashboard.value.pending_comment_count },
]);

const fetchDashboard = async () => {
  loading.value = true;
  try {
    const { data } = await http.get("/social/admin/dashboard/");
    dashboard.value = data;
  } finally {
    loading.value = false;
  }
};

const runBatchTask = async (taskType) => {
  actionLoading.value = taskType;
  batchResult.value = null;
  try {
    const payload =
      taskType === "accounts"
        ? { task_type: taskType, count: batchForms.accounts.count, start_number: batchForms.accounts.start_number }
        : { task_type: taskType, count: batchForms[taskType].count };

    const { data } = await http.post("/social/admin/batch-seed/", payload);
    batchResult.value = data;
    uiStore.pushToast(data.message || "批量任务执行成功", "success");
    await fetchDashboard();
  } finally {
    actionLoading.value = "";
  }
};

onMounted(() => {
  if (authStore.user?.is_staff) {
    fetchDashboard();
  }
});
</script>

<template>
  <section v-if="authStore.user?.is_staff" class="page admin-dashboard-page">
    <section class="panel admin-hero">
      <div class="split admin-hero-head">
        <div>
          <p class="eyebrow">管理后台</p>
          <h2>系统统计与批量数据管理</h2>
          <p class="muted">可查看平台关键指标，也可以直接批量生成测试账号、景点和社区帖子。</p>
        </div>
        <button class="btn btn-secondary" :disabled="loading" @click="fetchDashboard">
          {{ loading ? "刷新中..." : "刷新统计" }}
        </button>
      </div>
    </section>

    <section class="grid-3 admin-stat-grid">
      <article v-for="item in statCards" :key="item.label" class="card admin-stat-card">
        <p class="eyebrow">{{ item.label }}</p>
        <div class="metric">{{ item.value }}</div>
      </article>
    </section>

    <section class="grid-3 admin-tools-grid">
      <article class="panel admin-tool-card">
        <p class="eyebrow">批量账号生成</p>
        <h3>账号密码一致</h3>
        <div class="form-grid">
          <input v-model.number="batchForms.accounts.start_number" class="input" type="number" min="1000" placeholder="起始账号" />
          <input v-model.number="batchForms.accounts.count" class="input" type="number" min="1" max="200" placeholder="生成数量" />
          <button class="btn btn-primary" :disabled="actionLoading === 'accounts'" @click="runBatchTask('accounts')">
            {{ actionLoading === "accounts" ? "生成中..." : "生成账号" }}
          </button>
        </div>
        <p class="muted">例如起始账号为 1111，生成后密码将与账号保持一致。</p>
      </article>

      <article class="panel admin-tool-card">
        <p class="eyebrow">批量景点推送</p>
        <h3>快速补充景点素材</h3>
        <div class="form-grid">
          <input v-model.number="batchForms.destinations.count" class="input" type="number" min="1" max="200" placeholder="推送数量" />
          <button class="btn btn-primary" :disabled="actionLoading === 'destinations'" @click="runBatchTask('destinations')">
            {{ actionLoading === "destinations" ? "推送中..." : "生成景点" }}
          </button>
        </div>
        <p class="muted">系统会自动按省市生成景点名、简介、标签和基础评分。</p>
      </article>

      <article class="panel admin-tool-card">
        <p class="eyebrow">批量帖子上传</p>
        <h3>随机绑定现有用户</h3>
        <div class="form-grid">
          <input v-model.number="batchForms.posts.count" class="input" type="number" min="1" max="200" placeholder="生成数量" />
          <button class="btn btn-primary" :disabled="actionLoading === 'posts'" @click="runBatchTask('posts')">
            {{ actionLoading === "posts" ? "上传中..." : "生成帖子" }}
          </button>
        </div>
        <p class="muted">会随机选取用户与景点生成社区帖子，并自动设为可见状态。</p>
      </article>
    </section>

    <section v-if="batchResult" class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">任务结果</p>
          <h3>{{ batchResult.message }}</h3>
        </div>
        <span class="pill">新增 {{ batchResult.created_count }}</span>
      </div>
      <div class="form-grid" style="margin-top: 16px;">
        <div v-for="(item, index) in (batchResult.items || [])" :key="index" class="card">
          <template v-if="batchResult.task_type === 'accounts'">
            <strong>{{ item.username }}</strong>
            <p class="muted">密码：{{ item.password }}</p>
          </template>
          <template v-else-if="batchResult.task_type === 'destinations'">
            <strong>{{ item.name }}</strong>
            <p class="muted">{{ item.city }} · {{ item.province }}</p>
          </template>
          <template v-else>
            <strong>{{ item.title }}</strong>
            <p class="muted">{{ item.author }} · {{ item.destination }}</p>
          </template>
        </div>
      </div>
    </section>

    <section class="grid-2">
      <article class="panel">
        <div class="split">
          <div>
            <p class="eyebrow">近 7 天趋势</p>
            <h3>用户、帖子与景点新增情况</h3>
          </div>
          <p class="muted">{{ loading ? "加载中..." : `共 ${dashboard.recent_trends.length} 天数据` }}</p>
        </div>

        <div class="form-grid" style="margin-top: 18px;">
          <div v-if="!dashboard.recent_trends.length" class="card muted">当前暂无近 7 天趋势数据。</div>
          <article v-for="item in dashboard.recent_trends" :key="item.date" class="card">
            <div class="split">
              <h4>{{ item.date }}</h4>
              <span class="pill">合计 {{ item.user_count + item.post_count + item.destination_count }}</span>
            </div>
            <div class="form-grid">
              <div class="rating-bar-row">
                <span>用户</span>
                <div class="progress-track admin-track">
                  <div class="progress-bar admin-bar" :style="{ width: `${(item.user_count / maxTrendCount) * 100}%` }"></div>
                </div>
                <span class="muted">{{ item.user_count }}</span>
              </div>
              <div class="rating-bar-row">
                <span>帖子</span>
                <div class="progress-track admin-track">
                  <div class="progress-bar admin-bar" :style="{ width: `${(item.post_count / maxTrendCount) * 100}%` }"></div>
                </div>
                <span class="muted">{{ item.post_count }}</span>
              </div>
              <div class="rating-bar-row">
                <span>景点</span>
                <div class="progress-track admin-track">
                  <div class="progress-bar admin-bar" :style="{ width: `${(item.destination_count / maxTrendCount) * 100}%` }"></div>
                </div>
                <span class="muted">{{ item.destination_count }}</span>
              </div>
            </div>
          </article>
        </div>
      </article>

      <article class="panel">
        <div class="split">
          <div>
            <p class="eyebrow">发帖时段统计</p>
            <h3>按日期与 6 小时时段查看发帖数量</h3>
          </div>
          <p class="muted">{{ loading ? "加载中..." : `共 ${dashboard.timeline.length} 天数据` }}</p>
        </div>

        <div class="form-grid" style="margin-top: 18px;">
          <div v-if="!dashboard.timeline.length" class="card muted">当前暂无帖子统计数据。</div>
          <article v-for="item in dashboard.timeline" :key="item.date" class="card">
            <div class="split">
              <div>
                <h4>{{ item.date }}</h4>
                <p class="muted">当日发帖总数 {{ item.total }}</p>
              </div>
            </div>
            <div class="form-grid">
              <div v-for="segment in item.segments" :key="segment.label" class="rating-bar-row">
                <span>{{ segment.label }}</span>
                <div class="progress-track admin-track">
                  <div class="progress-bar admin-bar" :style="{ width: `${(segment.count / maxTimelineCount) * 100}%` }"></div>
                </div>
                <span class="muted">{{ segment.count }}</span>
              </div>
            </div>
          </article>
        </div>
      </article>
    </section>
  </section>

  <section v-else class="panel">
    <p class="eyebrow">管理后台</p>
    <h3>当前账号没有管理员权限</h3>
    <p class="muted">请使用管理员账号登录后查看统计数据和批量生成工具。</p>
  </section>
</template>
