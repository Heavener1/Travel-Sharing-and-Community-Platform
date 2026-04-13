<script setup>
import { computed, reactive, ref, watch } from "vue";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const saveMessage = ref("");
const saveError = ref("");
const avatarPreview = ref("");
const fieldErrors = reactive({});

const profileForm = reactive({
  first_name: "",
  nickname: "",
  bio: "",
  city: "",
  preferred_style: "",
  avatar: "",
  travel_level: "",
  phone: "",
  gender: "",
  birthday: "",
  occupation: "",
  signature: "",
  homepage: "",
});

const avatarError = computed(() => fieldErrors.avatar?.[0] || "");
const travelLevelError = computed(() => fieldErrors.travel_level?.[0] || "");
const birthdayError = computed(() => fieldErrors.birthday?.[0] || "");

const clearMessages = () => {
  saveMessage.value = "";
  saveError.value = "";
  Object.keys(fieldErrors).forEach((key) => delete fieldErrors[key]);
};

const syncForm = (user = authStore.user) => {
  if (!user) return;
  profileForm.first_name = user.first_name || "";
  profileForm.nickname = user.profile?.nickname || "";
  profileForm.bio = user.profile?.bio || "";
  profileForm.city = user.profile?.city || "";
  profileForm.preferred_style = user.profile?.preferred_style || "";
  profileForm.avatar = user.profile?.avatar_reference || "";
  profileForm.travel_level = user.profile?.travel_level || "";
  profileForm.phone = user.profile?.phone || "";
  profileForm.gender = user.profile?.gender || "";
  profileForm.birthday = user.profile?.birthday || "";
  profileForm.occupation = user.profile?.occupation || "";
  profileForm.signature = user.profile?.signature || "";
  profileForm.homepage = user.profile?.homepage || "";
  avatarPreview.value = user.avatar || user.profile?.avatar || "";
};

watch(
  () => authStore.user,
  (user) => {
    if (user) {
      syncForm(user);
    }
  },
  { deep: true, immediate: true },
);

const uploadAvatar = async (event) => {
  clearMessages();
  const file = event.target.files?.[0];
  if (!file) return;
  const payload = new FormData();
  payload.append("file", file);
  try {
    const { data } = await http.post("/travel/upload/", payload, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    profileForm.avatar = data.reference || "";
    avatarPreview.value = data.url || "";
    saveMessage.value = "头像已上传，记得点击“保存资料”后生效。";
  } catch (error) {
    const data = error?.response?.data || {};
    Object.assign(fieldErrors, data);
    saveError.value = data.detail || "头像上传失败，请稍后重试。";
  } finally {
    event.target.value = "";
  }
};

const saveProfile = async () => {
  clearMessages();
  try {
    const { data } = await http.patch("/auth/me/", profileForm);
    authStore.user = data;
    syncForm(data);
    saveMessage.value = "资料保存成功。";
  } catch (error) {
    const data = error?.response?.data || {};
    Object.assign(fieldErrors, data);
    saveError.value = data.detail || "保存失败，请检查表单中的提示信息。";
  }
};
</script>

<template>
  <section v-if="authStore.user" class="grid-2">
    <article class="panel">
      <p class="eyebrow">个人资料</p>
      <div class="profile-center">
        <img v-if="avatarPreview" :src="avatarPreview" alt="avatar" class="profile-avatar" />
        <div>
          <h3>{{ profileForm.nickname || authStore.user.username }}</h3>
          <p class="muted">{{ profileForm.signature || "还没有设置个性签名。" }}</p>
        </div>
      </div>

      <p v-if="saveMessage" class="muted">{{ saveMessage }}</p>
      <p v-if="saveError" class="muted">{{ saveError }}</p>

      <div class="form-grid">
        <label class="muted">上传头像</label>
        <input class="input" type="file" accept="image/*" @change="uploadAvatar" />
        <p v-if="avatarError" class="muted">{{ avatarError }}</p>
        <input v-model="profileForm.nickname" class="input" placeholder="昵称" />
        <p v-if="fieldErrors.nickname?.[0]" class="muted">{{ fieldErrors.nickname[0] }}</p>

        <input v-model="profileForm.first_name" class="input" placeholder="姓名" />
        <p v-if="fieldErrors.first_name?.[0]" class="muted">{{ fieldErrors.first_name[0] }}</p>

        <input :value="authStore.user.email || ''" class="input" placeholder="邮箱" readonly />
        <p class="muted">邮箱为注册信息，个人中心内不可修改。</p>

        <input v-model="profileForm.phone" class="input" placeholder="手机号" />
        <p v-if="fieldErrors.phone?.[0]" class="muted">{{ fieldErrors.phone[0] }}</p>

        <input v-model="profileForm.city" class="input" placeholder="所在城市" />
        <p v-if="fieldErrors.city?.[0]" class="muted">{{ fieldErrors.city[0] }}</p>

        <input v-model="profileForm.occupation" class="input" placeholder="职业" />
        <p v-if="fieldErrors.occupation?.[0]" class="muted">{{ fieldErrors.occupation[0] }}</p>

        <input
          v-model="profileForm.travel_level"
          class="input"
          placeholder="旅行等级，例如：旅行新人 / 资深背包客"
        />
        <p v-if="travelLevelError" class="muted">{{ travelLevelError }}</p>

        <input v-model="profileForm.preferred_style" class="input" placeholder="偏好风格" />
        <p v-if="fieldErrors.preferred_style?.[0]" class="muted">{{ fieldErrors.preferred_style[0] }}</p>

        <select v-model="profileForm.gender" class="select">
          <option value="">选择性别</option>
          <option value="male">男</option>
          <option value="female">女</option>
          <option value="other">其他</option>
        </select>
        <p v-if="fieldErrors.gender?.[0]" class="muted">{{ fieldErrors.gender[0] }}</p>

        <input v-model="profileForm.birthday" class="input" type="date" />
        <p v-if="birthdayError" class="muted">{{ birthdayError }}</p>

        <input v-model="profileForm.homepage" class="input" placeholder="个人主页" />
        <p v-if="fieldErrors.homepage?.[0]" class="muted">{{ fieldErrors.homepage[0] }}</p>

        <input v-model="profileForm.signature" class="input" placeholder="个性签名" />
        <p v-if="fieldErrors.signature?.[0]" class="muted">{{ fieldErrors.signature[0] }}</p>

        <textarea v-model="profileForm.bio" class="textarea" placeholder="个人简介"></textarea>
        <p v-if="fieldErrors.bio?.[0]" class="muted">{{ fieldErrors.bio[0] }}</p>

        <button class="btn btn-primary" @click="saveProfile">保存资料</button>
      </div>
    </article>

    <article class="panel">
      <p class="eyebrow">账户信息</p>
      <div class="form-grid">
        <div class="card"><strong>用户名：</strong>{{ authStore.user.username }}</div>
        <div class="card"><strong>账户类型：</strong>{{ authStore.user.is_staff ? "管理员账户" : "普通用户" }}</div>
        <div class="card"><strong>注册邮箱：</strong>{{ authStore.user.email || "未设置" }}</div>
        <div class="card"><strong>头像文件：</strong>{{ profileForm.avatar || "默认头像" }}</div>
        <button class="btn btn-secondary" @click="authStore.logout">退出登录</button>
      </div>
    </article>
  </section>

  <section v-else class="panel">
    <p class="eyebrow">个人中心</p>
    <h3>当前未登录</h3>
    <p class="muted">请使用右上角的登录或注册按钮打开弹窗进行操作。</p>
  </section>
</template>
