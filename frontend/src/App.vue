<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "./stores/auth";
import http from "./api/http";

const route = useRoute();
const authStore = useAuthStore();

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
    { label: "社区", to: "/community" },
    { label: "行程规划", to: "/planner" },
  ];
  if (authStore.user?.is_staff) {
    items.push({ label: "管理后台", to: "/admin-panel" });
  }
  items.push({ label: "我的", to: "/profile" });
  return items;
});

const routeTitle = computed(() => route.meta.title || "旅游分享与交流平台");

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

const submitLogin = async () => {
  authError.value = "";
  try {
    await authStore.login(loginForm);
    closeAuthModal();
  } catch (error) {
    authError.value =
      error?.response?.data?.non_field_errors?.[0] ||
      error?.response?.data?.detail ||
      "登录失败，请检查输入信息。";
    await refreshCaptcha();
  }
};

const submitRegister = async () => {
  authError.value = "";
  try {
    await authStore.register(registerForm);
    closeAuthModal();
  } catch (error) {
    authError.value =
      error?.response?.data?.non_field_errors?.[0] ||
      error?.response?.data?.detail ||
      "注册失败，请检查输入信息。";
    await refreshCaptcha();
  }
};

onMounted(() => {
  authStore.restore();
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
              <span>{{ authStore.user?.nickname || authStore.user?.username }}</span>
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
          <span>{{ authStore.isAuthenticated ? (authStore.user?.nickname || authStore.user?.username) : "游客模式" }}</span>
        </div>
      </section>

      <RouterView />
    </main>

    <div v-if="authModalOpen" class="modal-backdrop" @click.self="closeAuthModal">
      <div class="modal-card">
        <div class="split">
          <div class="action-row">
            <button class="btn" :class="authMode === 'login' ? 'btn-primary' : 'btn-secondary'" @click="authMode = 'login'">登录</button>
            <button class="btn" :class="authMode === 'register' ? 'btn-primary' : 'btn-secondary'" @click="authMode = 'register'">注册</button>
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
