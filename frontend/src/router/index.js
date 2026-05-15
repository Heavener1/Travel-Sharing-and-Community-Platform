/**
 * Vue Router 配置 — 9 条路由，全部懒加载。
 * beforeEach: 触发路由加载动画；afterEach: 更新页面标题。
 */
import { createRouter, createWebHistory } from "vue-router";

import { pinia } from "../stores";
import { useUiStore } from "../stores/ui";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    { path: "/", component: () => import("../views/HomeView.vue"), meta: { title: "首页概览" } },
    { path: "/explore", component: () => import("../views/ExploreView.vue"), meta: { title: "景点探索" } },
    { path: "/explore/:id", component: () => import("../views/ScenicDetailView.vue"), meta: { title: "景点详情" } },
    { path: "/qa", component: () => import("../views/ScenicQAView.vue"), meta: { title: "景点智能问答" } },
    { path: "/community", component: () => import("../views/CommunityView.vue"), meta: { title: "旅行社区" } },
    { path: "/community/:id", component: () => import("../views/PostDetailView.vue"), meta: { title: "帖子详情" } },
    { path: "/planner", component: () => import("../views/PlannerView.vue"), meta: { title: "智能行程规划" } },
    { path: "/admin-panel", component: () => import("../views/AdminDashboardView.vue"), meta: { title: "管理后台" } },
    { path: "/profile", component: () => import("../views/ProfileView.vue"), meta: { title: "个人中心" } },
  ],
});

router.beforeEach((to, from, next) => {
  const uiStore = useUiStore(pinia);
  if (to.fullPath !== from.fullPath) {
    uiStore.setRouteLoading(true);
  }
  next();
});

router.afterEach((to) => {
  const uiStore = useUiStore(pinia);
  window.setTimeout(() => {
    uiStore.setRouteLoading(false);
  }, 180);
  if (to.meta.title) {
    document.title = `${to.meta.title} | 旅迹共鸣`;
  }
});

export default router;
