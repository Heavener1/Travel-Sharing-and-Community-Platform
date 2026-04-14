import { createRouter, createWebHistory } from "vue-router";

import AdminDashboardView from "../views/AdminDashboardView.vue";
import CommunityView from "../views/CommunityView.vue";
import ExploreView from "../views/ExploreView.vue";
import HomeView from "../views/HomeView.vue";
import PlannerView from "../views/PlannerView.vue";
import PostDetailView from "../views/PostDetailView.vue";
import ProfileView from "../views/ProfileView.vue";
import ScenicDetailView from "../views/ScenicDetailView.vue";
import ScenicQAView from "../views/ScenicQAView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView, meta: { title: "首页概览" } },
    { path: "/explore", component: ExploreView, meta: { title: "景点探索" } },
    { path: "/explore/:id", component: ScenicDetailView, meta: { title: "景点详情" } },
    { path: "/qa", component: ScenicQAView, meta: { title: "景点智能问答" } },
    { path: "/community", component: CommunityView, meta: { title: "旅行社区" } },
    { path: "/community/:id", component: PostDetailView, meta: { title: "帖子详情" } },
    { path: "/planner", component: PlannerView, meta: { title: "智能行程规划" } },
    { path: "/admin-panel", component: AdminDashboardView, meta: { title: "管理后台" } },
    { path: "/profile", component: ProfileView, meta: { title: "个人中心" } },
  ],
});

export default router;
