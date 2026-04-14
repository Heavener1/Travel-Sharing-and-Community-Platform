<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";

import http from "./api/http";
import { useAuthStore } from "./stores/auth";
import { useNotificationStore } from "./stores/notifications";

const route = useRoute();
const authStore = useAuthStore();
const notificationStore = useNotificationStore();

const authModalOpen = ref(false);
const authMode = ref("login");
const authError = ref("");
const captcha = reactive({ key: "", image: "" });

const loginForm = reactive({
  username: "demo",
  password: "demo123456",
  captcha_key: "",
  captcha_code: "",
});

const registerForm = reactive({
  username: "",
  password: "",
  email: "",
  first_name: "",
  nickname: "",
  captcha_key: "",
  captcha_code: "",
});

const navItems = computed(() => {
  const items = [
    { label: "首页", to: "/" },
    { label: "景点探索", to: "/explore" },
    { label: "智能问答", to: "/qa" },
    { label: "旅行社区", to: "/community" },
    { label: "智能行程规划", to: "/planner" },
  ];
  if (authStore.user?.is_staff) {
    items.push({ label: "管理后台", to: "/admin-panel" });
  }
  items.push({ label: "个人中心", to: "/profile" });
  return items;
});

const routeTitle = computed(() => route.meta.title || "旅游分享与交流平台");
const displayName = computed(() => authStore.user?.display_name || authStore.user?.nickname || authStore.user?.first_name || authStore.user?.email || authStore.user?.username || "游客模式");

const refreshCaptcha = async () => {
  const { data } = await http.get("/auth/captcha/");
  captcha.key = data.captcha_key;
  captcha.image = data.image;
  loginForm.captcha_key = data.captcha_key;
  registerForm.captcha_key = data.captcha_key;
  loginForm.captcha_code = "";
  registerForm.captcha_code = "";
};

const openAuthModal = async (mode = "login") => {
  authMode.value = mode;
  authError.value = "";
  await refreshCaptcha();
  authModalOpen.value = true;
};

const closeAuthModal = () => {
  authModalOpen.value = false;
  authError.value = "";
};

const extractErrorMessage = (error, fallback) =>
  error?.response?.data?.non_field_errors?.[0] ||
  error?.response?.data?.detail ||
  fallback;

const submitLogin = async () => {
  authError.value = "";
  try {
    await authStore.login(loginForm);
    closeAuthModal();
  } catch (error) {
    authError.value = extractErrorMessage(error, "登录失败，请检查输入信息。");
    await refreshCaptcha();
  }
};

const submitRegister = async () => {
  authError.value = "";
  try {
    await authStore.register(registerForm);
    closeAuthModal();
  } catch (error) {
    authError.value = extractErrorMessage(error, "注册失败，请检查输入信息。");
    await refreshCaptcha();
  }
};

const handleNotificationClick = async () => {
  try {
    await notificationStore.togglePanel();
  } catch {
    notificationStore.open = !notificationStore.open;
  }
};

watch(
  () => authStore.isAuthenticated,
  async (authenticated) => {
    if (authenticated) {
      try {
        await notificationStore.fetchNotifications();
      } catch {
        notificationStore.reset();
        return;
      }
      notificationStore.startPolling();
      return;
    }
    notificationStore.reset();
  },
  { immediate: false },
);

watch(
  () => route.fullPath,
  () => {
    if (notificationStore.open) {
      notificationStore.open = false;
    }
  },
);

onMounted(async () => {
  await authStore.restore();
  if (authStore.isAuthenticated) {
    try {
      await notificationStore.fetchNotifications();
      notificationStore.startPolling();
    } catch {
      notificationStore.reset();
    }
  }
});

onBeforeUnmount(() => {
  notificationStore.stopPolling();
});
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">TRAVEL STORY HUB</p>
        <h1>旅迹共鸣</h1>
      </div>
      <div class="nav-wrap">
        <nav class="nav">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-link">
            {{ item.label }}
          </RouterLink>
        </nav>
        <div class="action-row">
          <template v-if="authStore.isAuthenticated">
            <div class="profile-chip profile-chip-rich">
              <img v-if="authStore.user?.avatar" :src="authStore.user.avatar" alt="avatar" class="mini-avatar" />
              <span>{{ displayName }}</span>
            </div>
            <button class="btn btn-secondary" @click="authStore.logout">退出</button>
          </template>
          <template v-else>
            <button class="btn btn-secondary" @click="openAuthModal('login')">登录</button>
            <button class="btn btn-primary" @click="openAuthModal('register')">注册</button>
          </template>
        </div>
      </div>
    </header>

    <main class="page">
      <section class="page-header">
        <div>
          <p class="eyebrow">毕业设计演示系统</p>
          <h2>{{ routeTitle }}</h2>
        </div>
        <div class="profile-chip profile-chip-rich">
          <img v-if="authStore.user?.avatar" :src="authStore.user.avatar" alt="avatar" class="mini-avatar" />
          <span>{{ displayName }}</span>
        </div>
      </section>

      <RouterView />
    </main>

    <div v-if="authStore.isAuthenticated" class="notification-fab-wrap">
      <button class="notification-fab" @click="handleNotificationClick">
        <span>消息</span>
        <span v-if="notificationStore.unreadCount" class="notification-badge">
          {{ notificationStore.unreadCount > 99 ? "99+" : notificationStore.unreadCount }}
        </span>
      </button>

      <div v-if="notificationStore.open" class="notification-panel">
        <div class="split notification-panel-head">
          <div>
            <p class="eyebrow">消息通知</p>
            <h3>最近互动</h3>
          </div>
          <button class="btn btn-secondary btn-compact" @click="notificationStore.open = false">关闭</button>
        </div>

        <div v-if="notificationStore.loading" class="card muted">正在加载消息...</div>
        <div v-else-if="!notificationStore.items.length" class="card muted">暂时还没有收到新的互动消息。</div>

        <div v-else class="form-grid">
          <RouterLink
            v-for="item in notificationStore.items"
            :key="item.id"
            :to="item.post ? `/community/${item.post}` : '/community'"
            class="notification-item"
          >
            <img v-if="item.actor_avatar" :src="item.actor_avatar" alt="actor avatar" class="mini-avatar" />
            <div class="notification-copy">
              <strong>{{ item.message }}</strong>
              <p class="muted">{{ item.post_title || "相关内容" }}</p>
              <p class="muted">{{ item.created_at }}</p>
            </div>
            <span v-if="!item.is_read" class="notification-dot"></span>
          </RouterLink>
        </div>
      </div>
    </div>

    <div v-if="authModalOpen" class="modal-backdrop" @click.self="closeAuthModal">
      <div class="modal-card">
        <div class="split">
          <div class="action-row">
            <button class="btn" :class="authMode === 'login' ? 'btn-primary' : 'btn-secondary'" @click="authMode = 'login'">
              登录
            </button>
            <button class="btn" :class="authMode === 'register' ? 'btn-primary' : 'btn-secondary'" @click="authMode = 'register'">
              注册
            </button>
          </div>
          <button class="btn btn-secondary" @click="closeAuthModal">关闭</button>
        </div>

        <p v-if="authError" class="muted">{{ authError }}</p>

        <div v-if="authMode === 'login'" class="form-grid">
          <input v-model="loginForm.username" class="input" placeholder="用户名" />
          <input v-model="loginForm.password" class="input" type="password" placeholder="密码" />
          <div class="captcha-row">
            <input v-model="loginForm.captcha_code" class="input" placeholder="图形验证码" />
            <img :src="captcha.image" alt="captcha" class="captcha-image" @click="refreshCaptcha" />
          </div>
          <button class="btn btn-primary" @click="submitLogin">登录</button>
        </div>

        <div v-else class="form-grid">
          <input v-model="registerForm.username" class="input" placeholder="用户名" />
          <input v-model="registerForm.nickname" class="input" placeholder="昵称" />
          <input v-model="registerForm.first_name" class="input" placeholder="姓名" />
          <input v-model="registerForm.email" class="input" placeholder="邮箱" />
          <input v-model="registerForm.password" class="input" type="password" placeholder="密码" />
          <div class="captcha-row">
            <input v-model="registerForm.captcha_code" class="input" placeholder="图形验证码" />
            <img :src="captcha.image" alt="captcha" class="captcha-image" @click="refreshCaptcha" />
          </div>
          <button class="btn btn-primary" @click="submitRegister">注册并登录</button>
        </div>
      </div>
    </div>
  </div>
</template>
