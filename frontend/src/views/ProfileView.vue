<script setup>
import { computed, reactive, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import http from "../api/http";
import { fetchFavoriteDestinations, fetchFavoritePosts, removeDestinationFavorites, removePostFavorites } from "../api/favorites";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";
import { clearFavoriteIds } from "../utils/collection";

const authStore = useAuthStore();
const uiStore = useUiStore();

const saveMessage = ref("");
const saveError = ref("");
const avatarPreview = ref("");
const dashboardLoading = ref(false);
const favoriteLoading = ref(false);
const favoritePostPage = ref(1);
const favoriteDestinationPage = ref(1);
const fieldErrors = reactive({});

const favoriteFilter = reactive({
  postKeyword: "",
  destinationKeyword: "",
  postSort: "latest",
  destinationSort: "latest",
});

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

const favoritePosts = ref([]);
const favoriteDestinations = ref([]);
const selectedFavoritePosts = ref([]);
const selectedFavoriteDestinations = ref([]);
const favoritePageSize = 4;

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

const favoriteSummary = computed(() => ({
  posts: favoritePosts.value.length,
  destinations: favoriteDestinations.value.length,
}));

const displayName = computed(
  () => authStore.user?.display_name || profileForm.nickname || profileForm.first_name || authStore.user?.email || authStore.user?.username || "未登录用户",
);

const profileStats = computed(() => [
  { label: "我的帖子", value: dashboard.value.stats.post_count },
  { label: "我的行程", value: dashboard.value.stats.trip_count },
  { label: "我的评价", value: dashboard.value.stats.review_count },
  { label: "收藏景点", value: favoriteSummary.value.destinations },
  { label: "收藏帖子", value: favoriteSummary.value.posts },
  { label: "已通过帖子", value: dashboard.value.stats.approved_post_count },
]);

const sortFavorites = (items, sortType, nameAccessor) => {
  const sorted = [...items];
  if (sortType === "latest") sorted.sort((a, b) => new Date(b.favorited_at || 0) - new Date(a.favorited_at || 0));
  if (sortType === "earliest") sorted.sort((a, b) => new Date(a.favorited_at || 0) - new Date(b.favorited_at || 0));
  if (sortType === "name") sorted.sort((a, b) => String(nameAccessor(a)).localeCompare(String(nameAccessor(b)), "zh-CN"));
  return sorted;
};

const filteredFavoritePosts = computed(() => {
  const keyword = favoriteFilter.postKeyword.trim().toLowerCase();
  const items = favoritePosts.value.filter((item) => {
    if (!keyword) return true;
    return [item.title, item.author_name, item.destination_name].join(" ").toLowerCase().includes(keyword);
  });
  return sortFavorites(items, favoriteFilter.postSort, (item) => item.title);
});

const filteredFavoriteDestinations = computed(() => {
  const keyword = favoriteFilter.destinationKeyword.trim().toLowerCase();
  const items = favoriteDestinations.value.filter((item) => {
    if (!keyword) return true;
    return [item.name, item.city, item.province, item.summary].join(" ").toLowerCase().includes(keyword);
  });
  return sortFavorites(items, favoriteFilter.destinationSort, (item) => item.name);
});

const favoritePostPageCount = computed(() => Math.max(1, Math.ceil(filteredFavoritePosts.value.length / favoritePageSize)));
const favoriteDestinationPageCount = computed(() => Math.max(1, Math.ceil(filteredFavoriteDestinations.value.length / favoritePageSize)));

const pagedFavoritePosts = computed(() => {
  const start = (favoritePostPage.value - 1) * favoritePageSize;
  return filteredFavoritePosts.value.slice(start, start + favoritePageSize);
});

const pagedFavoriteDestinations = computed(() => {
  const start = (favoriteDestinationPage.value - 1) * favoritePageSize;
  return filteredFavoriteDestinations.value.slice(start, start + favoritePageSize);
});

const allCurrentPostsSelected = computed(
  () => pagedFavoritePosts.value.length > 0 && pagedFavoritePosts.value.every((item) => selectedFavoritePosts.value.includes(item.id)),
);

const allCurrentDestinationsSelected = computed(
  () => pagedFavoriteDestinations.value.length > 0 && pagedFavoriteDestinations.value.every((item) => selectedFavoriteDestinations.value.includes(item.id)),
);

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

const clampFavoritePages = () => {
  favoritePostPage.value = Math.min(favoritePostPage.value, favoritePostPageCount.value);
  favoriteDestinationPage.value = Math.min(favoriteDestinationPage.value, favoriteDestinationPageCount.value);
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

const fetchFavorites = async () => {
  favoriteLoading.value = true;
  try {
    const [postEntries, destinationEntries] = await Promise.all([
      fetchFavoritePosts(authStore.isAuthenticated),
      fetchFavoriteDestinations(authStore.isAuthenticated),
    ]);

    favoritePosts.value = postEntries.map((entry) => ({
      ...(entry.post || {}),
      id: entry.id,
      favorited_at: entry.favorited_at,
    }));

    favoriteDestinations.value = destinationEntries.map((entry) => ({
      ...(entry.destination || {}),
      id: entry.id,
      favorited_at: entry.favorited_at,
    }));

    selectedFavoritePosts.value = [];
    selectedFavoriteDestinations.value = [];
    clampFavoritePages();
  } finally {
    favoriteLoading.value = false;
  }
};

watch(
  () => [favoriteFilter.postKeyword, favoriteFilter.postSort],
  () => {
    favoritePostPage.value = 1;
    selectedFavoritePosts.value = [];
    clampFavoritePages();
  },
);

watch(
  () => [favoriteFilter.destinationKeyword, favoriteFilter.destinationSort],
  () => {
    favoriteDestinationPage.value = 1;
    selectedFavoriteDestinations.value = [];
    clampFavoritePages();
  },
);

watch(
  () => authStore.user,
  (user) => {
    if (user) {
      syncForm(user);
      fetchDashboard();
      fetchFavorites();
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

const toggleCurrentPageSelection = (type) => {
  if (type === "posts") {
    const currentIds = pagedFavoritePosts.value.map((item) => item.id);
    if (allCurrentPostsSelected.value) {
      selectedFavoritePosts.value = selectedFavoritePosts.value.filter((id) => !currentIds.includes(id));
    } else {
      selectedFavoritePosts.value = Array.from(new Set([...selectedFavoritePosts.value, ...currentIds]));
    }
    return;
  }
  const currentIds = pagedFavoriteDestinations.value.map((item) => item.id);
  if (allCurrentDestinationsSelected.value) {
    selectedFavoriteDestinations.value = selectedFavoriteDestinations.value.filter((id) => !currentIds.includes(id));
  } else {
    selectedFavoriteDestinations.value = Array.from(new Set([...selectedFavoriteDestinations.value, ...currentIds]));
  }
};

const removeSelectedFavorites = async (type) => {
  if (type === "posts" && selectedFavoritePosts.value.length) {
    await removePostFavorites(selectedFavoritePosts.value, authStore.isAuthenticated);
    favoritePosts.value = favoritePosts.value.filter((item) => !selectedFavoritePosts.value.includes(item.id));
    selectedFavoritePosts.value = [];
    clampFavoritePages();
    uiStore.pushToast("已移除选中的收藏帖子", "success");
    return;
  }
  if (type === "destinations" && selectedFavoriteDestinations.value.length) {
    await removeDestinationFavorites(selectedFavoriteDestinations.value, authStore.isAuthenticated);
    favoriteDestinations.value = favoriteDestinations.value.filter((item) => !selectedFavoriteDestinations.value.includes(item.id));
    selectedFavoriteDestinations.value = [];
    clampFavoritePages();
    uiStore.pushToast("已移除选中的收藏景点", "success");
  }
};

const clearAllFavorites = async (type) => {
  if (type === "posts") {
    await removePostFavorites(favoritePosts.value.map((item) => item.id), authStore.isAuthenticated);
    if (!authStore.isAuthenticated) clearFavoriteIds("travel_favorite_posts");
    favoritePosts.value = [];
    selectedFavoritePosts.value = [];
    favoritePostPage.value = 1;
    uiStore.pushToast("已清空帖子收藏", "success");
    return;
  }
  await removeDestinationFavorites(favoriteDestinations.value.map((item) => item.id), authStore.isAuthenticated);
  if (!authStore.isAuthenticated) clearFavoriteIds("travel_favorite_destinations");
  favoriteDestinations.value = [];
  selectedFavoriteDestinations.value = [];
  favoriteDestinationPage.value = 1;
  uiStore.pushToast("已清空景点收藏", "success");
};
</script>

<template>
  <section v-if="authStore.user" class="page profile-page">
    <section class="panel profile-hero-card">
      <div class="profile-hero">
        <div class="profile-hero-main">
          <img v-if="avatarPreview" :src="avatarPreview" alt="avatar" class="profile-avatar profile-avatar-large" />
          <div>
            <p class="eyebrow">个人中心</p>
            <h2>{{ displayName }}</h2>
            <p class="muted">{{ profileForm.signature || "还没有设置个性签名，补一句会更有记忆点。" }}</p>
            <div class="tag-row">
              <span class="tag">{{ profileForm.city || "城市待补充" }}</span>
              <span class="tag">{{ profileForm.travel_level || "旅行等级待补充" }}</span>
              <span class="tag">{{ profileForm.preferred_style || "偏好风格待补充" }}</span>
            </div>
          </div>
        </div>
        <div class="profile-hero-actions">
          <button class="btn btn-secondary" @click="authStore.logout">退出登录</button>
          <RouterLink v-if="authStore.user.is_staff" to="/admin-panel" class="btn btn-primary">进入管理后台</RouterLink>
        </div>
      </div>
    </section>

    <section class="grid-3 admin-stat-grid">
      <article v-for="item in profileStats" :key="item.label" class="card admin-stat-card">
        <p class="eyebrow">{{ item.label }}</p>
        <div class="metric">{{ item.value }}</div>
      </article>
    </section>

    <section class="profile-main-layout">
      <aside class="profile-sidebar">
        <article class="panel">
          <p class="eyebrow">账号信息</p>
          <div class="form-grid">
            <div class="card profile-info-card"><strong>显示名称</strong><p class="muted">{{ displayName }}</p></div>
            <div class="card profile-info-card"><strong>登录账号</strong><p class="muted">{{ authStore.user.username }}</p></div>
            <div class="card profile-info-card"><strong>注册邮箱</strong><p class="muted">{{ authStore.user.email || "未设置" }}</p></div>
            <div class="card profile-info-card"><strong>账号类型</strong><p class="muted">{{ authStore.user.is_staff ? "管理员账号" : "普通用户" }}</p></div>
            <div class="card profile-info-card"><strong>待处理帖子</strong><p class="muted">{{ dashboard.stats.pending_post_count }}</p></div>
          </div>
        </article>

        <article class="panel">
          <p class="eyebrow">个人名片</p>
          <div class="form-grid">
            <div class="card profile-info-card"><strong>职业</strong><p class="muted">{{ profileForm.occupation || "待补充" }}</p></div>
            <div class="card profile-info-card"><strong>手机号</strong><p class="muted">{{ profileForm.phone || "待补充" }}</p></div>
            <div class="card profile-info-card"><strong>生日</strong><p class="muted">{{ profileForm.birthday || "待补充" }}</p></div>
            <div class="card profile-info-card"><strong>主页</strong><p class="muted">{{ profileForm.homepage || "待补充" }}</p></div>
          </div>
        </article>
      </aside>

      <div class="profile-content">
        <section class="panel">
          <div class="split">
            <div>
              <p class="eyebrow">资料编辑</p>
              <h3>完善你的公开展示信息</h3>
            </div>
            <button class="btn btn-primary" @click="saveProfile">保存资料</button>
          </div>

          <p v-if="saveMessage" class="muted profile-feedback success-text">{{ saveMessage }}</p>
          <p v-if="saveError" class="muted profile-feedback">{{ saveError }}</p>

          <div class="profile-form-grid" style="margin-top: 18px;">
            <div class="profile-form-span-2 card avatar-upload-card">
              <label class="muted">上传头像</label>
              <div class="profile-avatar-upload-row">
                <img v-if="avatarPreview" :src="avatarPreview" alt="avatar preview" class="profile-avatar" />
                <div class="form-grid">
                  <input class="input" type="file" accept="image/*" @change="uploadAvatar" />
                  <p v-if="fieldErrors.avatar?.[0]" class="muted">{{ fieldErrors.avatar[0] }}</p>
                  <p class="muted">建议使用清晰的人像或旅行照片，方便在社区与评论中展示。</p>
                </div>
              </div>
            </div>

            <input v-model="profileForm.nickname" class="input" placeholder="昵称" />
            <input v-model="profileForm.first_name" class="input" placeholder="姓名" />
            <input :value="authStore.user.email || ''" class="input" placeholder="邮箱" readonly />
            <input v-model="profileForm.phone" class="input" placeholder="手机号" />
            <input v-model="profileForm.city" class="input" placeholder="所在城市" />
            <input v-model="profileForm.occupation" class="input" placeholder="职业" />
            <input v-model="profileForm.travel_level" class="input" placeholder="旅行等级" />
            <input v-model="profileForm.preferred_style" class="input" placeholder="偏好风格" />
            <select v-model="profileForm.gender" class="select">
              <option value="">选择性别</option>
              <option value="male">男</option>
              <option value="female">女</option>
              <option value="other">其他</option>
            </select>
            <input v-model="profileForm.birthday" class="input" type="date" />
            <input v-model="profileForm.homepage" class="input profile-form-span-2" placeholder="个人主页" />
            <input v-model="profileForm.signature" class="input profile-form-span-2" placeholder="个性签名" />
            <textarea v-model="profileForm.bio" class="textarea profile-form-span-2" placeholder="个人简介"></textarea>
          </div>
        </section>

        <section class="panel">
          <div class="split">
            <div>
              <p class="eyebrow">我的收藏</p>
              <h3>支持搜索、排序、分页和批量管理</h3>
            </div>
            <p class="muted">{{ favoriteLoading ? "加载中..." : `景点 ${favoriteSummary.destinations} · 帖子 ${favoriteSummary.posts}` }}</p>
          </div>

          <div class="favorite-manager-grid" style="margin-top: 16px;">
            <div class="card">
              <div class="split">
                <div>
                  <p class="eyebrow">收藏景点</p>
                  <h4>保留以后再去的目的地</h4>
                </div>
                <div class="action-row">
                  <button class="btn btn-secondary btn-compact" :disabled="!favoriteDestinations.length" @click="toggleCurrentPageSelection('destinations')">
                    {{ allCurrentDestinationsSelected ? "取消本页全选" : "本页全选" }}
                  </button>
                  <button class="btn btn-secondary btn-compact" :disabled="!selectedFavoriteDestinations.length" @click="removeSelectedFavorites('destinations')">
                    移除选中
                  </button>
                  <button class="btn btn-secondary btn-compact" :disabled="!favoriteDestinations.length" @click="clearAllFavorites('destinations')">
                    清空全部
                  </button>
                </div>
              </div>

              <div class="filter-bar">
                <input v-model="favoriteFilter.destinationKeyword" class="input" placeholder="搜索景点名称、城市、省份" />
                <select v-model="favoriteFilter.destinationSort" class="select">
                  <option value="latest">按收藏时间：最新</option>
                  <option value="earliest">按收藏时间：最早</option>
                  <option value="name">按名称排序</option>
                </select>
              </div>

              <div v-if="!filteredFavoriteDestinations.length" class="muted">当前没有匹配的收藏景点。</div>
              <div v-else class="form-grid">
                <label v-for="item in pagedFavoriteDestinations" :key="item.id" class="card favorite-manage-card">
                  <input v-model="selectedFavoriteDestinations" type="checkbox" :value="item.id" />
                  <RouterLink :to="`/explore/${item.id}`" class="favorite-link-card">
                    <strong>{{ item.name }}</strong>
                    <p class="muted">{{ item.city }} · {{ item.province }}</p>
                    <p class="muted">收藏于 {{ item.favorited_at ? new Date(item.favorited_at).toLocaleString("zh-CN") : "较早以前" }}</p>
                  </RouterLink>
                </label>

                <div class="pagination-row">
                  <button class="btn btn-secondary btn-compact" :disabled="favoriteDestinationPage <= 1" @click="favoriteDestinationPage -= 1">上一页</button>
                  <span class="muted">第 {{ favoriteDestinationPage }} / {{ favoriteDestinationPageCount }} 页</span>
                  <button class="btn btn-secondary btn-compact" :disabled="favoriteDestinationPage >= favoriteDestinationPageCount" @click="favoriteDestinationPage += 1">下一页</button>
                </div>
              </div>
            </div>

            <div class="card">
              <div class="split">
                <div>
                  <p class="eyebrow">收藏帖子</p>
                  <h4>随时回看灵感与攻略</h4>
                </div>
                <div class="action-row">
                  <button class="btn btn-secondary btn-compact" :disabled="!favoritePosts.length" @click="toggleCurrentPageSelection('posts')">
                    {{ allCurrentPostsSelected ? "取消本页全选" : "本页全选" }}
                  </button>
                  <button class="btn btn-secondary btn-compact" :disabled="!selectedFavoritePosts.length" @click="removeSelectedFavorites('posts')">
                    移除选中
                  </button>
                  <button class="btn btn-secondary btn-compact" :disabled="!favoritePosts.length" @click="clearAllFavorites('posts')">
                    清空全部
                  </button>
                </div>
              </div>

              <div class="filter-bar">
                <input v-model="favoriteFilter.postKeyword" class="input" placeholder="搜索帖子标题、作者、景点" />
                <select v-model="favoriteFilter.postSort" class="select">
                  <option value="latest">按收藏时间：最新</option>
                  <option value="earliest">按收藏时间：最早</option>
                  <option value="name">按标题排序</option>
                </select>
              </div>

              <div v-if="!filteredFavoritePosts.length" class="muted">当前没有匹配的收藏帖子。</div>
              <div v-else class="form-grid">
                <label v-for="item in pagedFavoritePosts" :key="item.id" class="card favorite-manage-card">
                  <input v-model="selectedFavoritePosts" type="checkbox" :value="item.id" />
                  <RouterLink :to="`/community/${item.id}`" class="favorite-link-card">
                    <strong>{{ item.title }}</strong>
                    <p class="muted">{{ item.author_name }} · {{ item.destination_name || "未关联景点" }}</p>
                    <p class="muted">收藏于 {{ item.favorited_at ? new Date(item.favorited_at).toLocaleString("zh-CN") : "较早以前" }}</p>
                  </RouterLink>
                </label>

                <div class="pagination-row">
                  <button class="btn btn-secondary btn-compact" :disabled="favoritePostPage <= 1" @click="favoritePostPage -= 1">上一页</button>
                  <span class="muted">第 {{ favoritePostPage }} / {{ favoritePostPageCount }} 页</span>
                  <button class="btn btn-secondary btn-compact" :disabled="favoritePostPage >= favoritePostPageCount" @click="favoritePostPage += 1">下一页</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="grid-3 profile-content-grid">
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
                    <p class="muted">{{ post.destination_name || "未关联景点" }}</p>
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
              <div v-if="!dashboard.recent_trips.length" class="card muted">你还没有生成行程，去智能行程规划页面试试看吧。</div>
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
                <h3>最近景点评分</h3>
              </div>
              <p class="muted">{{ dashboardLoading ? "加载中..." : `共 ${dashboard.stats.review_count} 条` }}</p>
            </div>
            <div class="form-grid" style="margin-top: 16px;">
              <div v-if="!dashboard.recent_reviews.length" class="card muted">你还没有评价景点，去景点详情页打个分吧。</div>
              <article v-for="review in dashboard.recent_reviews" :key="review.id" class="card">
                <div class="split">
                  <div>
                    <strong>{{ review.destination_name || "景点评价" }}</strong>
                    <p class="muted">{{ review.display_name || review.nickname || review.username }}</p>
                  </div>
                  <span class="pill">{{ review.rating }} 星</span>
                </div>
                <p class="summary-two-lines">{{ review.content || "本次仅进行了打分，没有填写文字评价。" }}</p>
              </article>
            </div>
          </article>
        </section>
      </div>
    </section>
  </section>

  <section v-else class="panel">
    <p class="eyebrow">个人中心</p>
    <h3>当前未登录</h3>
    <p class="muted">请使用右上角的登录或注册按钮打开弹窗进行操作。</p>
  </section>
</template>
