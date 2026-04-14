<script setup>
import { onMounted, reactive, ref, watch } from "vue";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const saveMessage = ref("");
const saveError = ref("");
const avatarPreview = ref("");
const dashboardLoading = ref(false);
const dashboard = ref({
  stats: {
    post_count: 0,
    approved_post_count: 0,
    pending_post_count: 0,
    trip_count: 0,
    review_count: 0,
  },
  recent_posts: [],
  recent_trips: [],
  recent_reviews: [],
});
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

const fetchDashboard = async () => {
  if (!authStore.isAuthenticated) return;
  dashboardLoading.value = true;
  try {
    const { data } = await http.get("/auth/dashboard/");
    dashboard.value = data;
  } finally {
    dashboardLoading.value = false;
  }
};

watch(
  () => authStore.user,
  (user) => {
    if (user) {
      syncForm(user);
      fetchDashboard();
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
    saveMessage.value = "头像已上传，点击“保存资料”后生效。";
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

onMounted(() => {
  if (authStore.user) {
    syncForm(authStore.user);
    fetchDashboard();
  }
});
</script>

<template>
  <section v-if="authStore.user" class="page">
    <section class="grid-3">
      <article class="card">
        <div class="metric">{{ dashboard.stats.post_count }}</div>
        <p class="muted">我发布的帖子</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.stats.trip_count }}</div>
        <p class="muted">我的行程方案</p>
      </article>
      <article class="card">
        <div class="metric">{{ dashboard.stats.review_count }}</div>
        <p class="muted">我的景点评价</p>
      </article>
    </section>

    <section class="grid-2 profile-layout">
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
          <p v-if="fieldErrors.avatar?.[0]" class="muted">{{ fieldErrors.avatar[0] }}</p>

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

          <input v-model="profileForm.travel_level" class="input" placeholder="旅行等级，例如：旅行新人 / 资深背包客" />
          <p v-if="fieldErrors.travel_level?.[0]" class="muted">{{ fieldErrors.travel_level[0] }}</p>

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
          <p v-if="fieldErrors.birthday?.[0]" class="muted">{{ fieldErrors.birthday[0] }}</p>

          <input v-model="profileForm.homepage" class="input" placeholder="个人主页" />
          <p v-if="fieldErrors.homepage?.[0]" class="muted">{{ fieldErrors.homepage[0] }}</p>

          <input v-model="profileForm.signature" class="input" placeholder="个性签名" />
          <p v-if="fieldErrors.signature?.[0]" class="muted">{{ fieldErrors.signature[0] }}</p>

          <textarea v-model="profileForm.bio" class="textarea" placeholder="个人简介"></textarea>
          <p v-if="fieldErrors.bio?.[0]" class="muted">{{ fieldErrors.bio[0] }}</p>

          <button class="btn btn-primary" @click="saveProfile">保存资料</button>
        </div>
      </article>

      <section class="form-grid">
        <article class="panel">
          <div class="split">
            <div>
              <p class="eyebrow">账户信息</p>
              <h3>我的账号概览</h3>
            </div>
            <button class="btn btn-secondary" @click="authStore.logout">退出登录</button>
          </div>
          <div class="form-grid" style="margin-top: 16px;">
            <div class="card"><strong>用户名：</strong>{{ authStore.user.username }}</div>
            <div class="card"><strong>账号类型：</strong>{{ authStore.user.is_staff ? "管理员账号" : "普通用户" }}</div>
            <div class="card"><strong>注册邮箱：</strong>{{ authStore.user.email || "未设置" }}</div>
            <div class="card"><strong>已通过审核帖子：</strong>{{ dashboard.stats.approved_post_count }}</div>
            <div class="card"><strong>待审核帖子：</strong>{{ dashboard.stats.pending_post_count }}</div>
            <div class="card"><strong>头像文件：</strong>{{ profileForm.avatar || "默认头像" }}</div>
          </div>
        </article>

        <article class="panel">
          <div class="split">
            <div>
              <p class="eyebrow">我的帖子</p>
              <h3>最近发布内容</h3>
            </div>
            <p class="muted">{{ dashboardLoading ? "加载中..." : `共 ${dashboard.stats.post_count} 篇` }}</p>
          </div>
          <div class="form-grid" style="margin-top: 16px;">
            <div v-if="!dashboard.recent_posts.length" class="card muted">你还没有发布帖子，可以去旅行社区分享第一篇故事。</div>
            <article v-for="post in dashboard.recent_posts" :key="post.id" class="card">
              <div class="split">
                <div>
                  <h4>{{ post.title }}</h4>
                  <p class="muted">{{ post.destination_name || "未关联景点" }} · {{ post.status }}</p>
                </div>
                <span class="pill">{{ post.like_count }} 赞 · {{ post.comment_count }} 评</span>
              </div>
              <p class="summary-two-lines">{{ post.content }}</p>
            </article>
          </div>
        </article>

        <article class="panel">
          <div class="split">
            <div>
              <p class="eyebrow">我的行程</p>
              <h3>最近生成方案</h3>
            </div>
            <p class="muted">{{ dashboardLoading ? "加载中..." : `共 ${dashboard.stats.trip_count} 个` }}</p>
          </div>
          <div class="form-grid" style="margin-top: 16px;">
            <div v-if="!dashboard.recent_trips.length" class="card muted">你还没有生成行程，去智能行程规划页试试吧。</div>
            <article v-for="trip in dashboard.recent_trips" :key="trip.id" class="card">
              <div class="split">
                <div>
                  <h4>{{ trip.title }}</h4>
                  <p class="muted">{{ trip.departure_city }} → {{ trip.destination_city }} · {{ trip.days }} 天</p>
                </div>
                <span class="pill">预算 {{ trip.budget }}</span>
              </div>
              <p class="muted">包含 {{ trip.stops.length }} 个景点站点</p>
            </article>
          </div>
        </article>

        <article class="panel">
          <div class="split">
            <div>
              <p class="eyebrow">我的评价</p>
              <h3>最近景点打分</h3>
            </div>
            <p class="muted">{{ dashboardLoading ? "加载中..." : `共 ${dashboard.stats.review_count} 条` }}</p>
          </div>
          <div class="form-grid" style="margin-top: 16px;">
            <div v-if="!dashboard.recent_reviews.length" class="card muted">你还没有评价景点，去景点详情页打个分吧。</div>
            <article v-for="review in dashboard.recent_reviews" :key="review.id" class="card">
              <div class="review-header">
                <div class="comment-line">
                  <img :src="review.author_avatar" alt="avatar" class="small-avatar mini-avatar" />
                  <div>
                    <strong>{{ review.nickname || review.username }}</strong>
                    <p class="muted">{{ review.destination_name || "景点评价" }}</p>
                  </div>
                </div>
                <span class="pill">{{ review.rating }} 星</span>
              </div>
              <p class="summary-two-lines">{{ review.content || "本次仅进行了打分，没有填写文字评价。" }}</p>
            </article>
          </div>
        </article>
      </section>
    </section>
  </section>

  <section v-else class="panel">
    <p class="eyebrow">个人中心</p>
    <h3>当前未登录</h3>
    <p class="muted">请使用右上角的登录或注册按钮打开弹窗进行操作。</p>
  </section>
</template>
