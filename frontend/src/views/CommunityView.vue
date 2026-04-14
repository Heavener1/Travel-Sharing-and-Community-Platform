<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";
import { getFavoriteIds, shareContent, toggleFavoriteId } from "../utils/collection";

const authStore = useAuthStore();
const uiStore = useUiStore();

const posts = ref([]);
const destinations = ref([]);
const loading = ref(true);
const favoritePostIds = ref([]);

const form = reactive({
  title: "",
  content: "",
  cover: "",
  destination: "",
  tags: "",
});

const coverPreview = ref("");
const commentDrafts = reactive({});
const replyDrafts = reactive({});
const postModalOpen = ref(false);
const commentModalOpen = ref(false);
const replyModalOpen = ref(false);
const activePostId = ref(null);
const activeCommentId = ref(null);

const feedFilter = reactive({
  destination: "all",
  sort: "latest",
});

const aiPolishLoading = ref(false);
const aiPolishProgress = ref(0);
const aiPolishStatus = ref("");
const aiPolishText = ref("");
const aiComparison = reactive({
  original: { title: "", tags: "", content: "" },
  polished: { title: "", tags: "", content: "" },
  selected: { title: "original", tags: "original", content: "original" },
});

const skeletonPosts = Array.from({ length: 4 }, (_, index) => ({ id: index }));
const postFavoriteStorageKey = "travel_favorite_posts";

const filteredPosts = computed(() => {
  const items = posts.value.filter((item) => feedFilter.destination === "all" || String(item.destination || "") === feedFilter.destination);
  const sorted = [...items];
  if (feedFilter.sort === "latest") {
    sorted.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }
  if (feedFilter.sort === "hot") {
    sorted.sort((a, b) => b.like_count + b.comment_count - (a.like_count + a.comment_count));
  }
  if (feedFilter.sort === "comments") {
    sorted.sort((a, b) => b.comment_count - a.comment_count);
  }
  return sorted;
});

const isPostFavorite = (postId) => favoritePostIds.value.includes(postId);

const fetchPosts = async () => {
  loading.value = true;
  try {
    const { data } = await http.get("/social/posts/");
    posts.value = data.results ?? data;
  } finally {
    loading.value = false;
  }
};

const fetchDestinations = async () => {
  const { data } = await http.get("/travel/destinations/");
  destinations.value = data.results ?? data;
};

const resetPostForm = () => {
  form.title = "";
  form.content = "";
  form.cover = "";
  form.destination = "";
  form.tags = "";
  coverPreview.value = "";
  aiPolishText.value = "";
  aiPolishProgress.value = 0;
  aiPolishStatus.value = "";
  aiComparison.original.title = "";
  aiComparison.original.tags = "";
  aiComparison.original.content = "";
  aiComparison.polished.title = "";
  aiComparison.polished.tags = "";
  aiComparison.polished.content = "";
  aiComparison.selected.title = "original";
  aiComparison.selected.tags = "original";
  aiComparison.selected.content = "original";
};

const applySelectedPolish = () => {
  form.title =
    aiComparison.selected.title === "polished" ? aiComparison.polished.title || aiComparison.original.title : aiComparison.original.title;
  form.tags = aiComparison.selected.tags === "polished" ? aiComparison.polished.tags || aiComparison.original.tags : aiComparison.original.tags;
  form.content =
    aiComparison.selected.content === "polished"
      ? aiComparison.polished.content || aiComparison.original.content
      : aiComparison.original.content;
};

const submitPost = async () => {
  await http.post("/social/posts/", form);
  resetPostForm();
  postModalOpen.value = false;
  await fetchPosts();
};

const uploadCover = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const payload = new FormData();
  payload.append("file", file);
  const { data } = await http.post("/travel/upload/", payload, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  form.cover = data.reference || data.url;
  coverPreview.value = data.url || data.reference || "";
  event.target.value = "";
};

const polishPost = async () => {
  aiPolishLoading.value = true;
  aiPolishProgress.value = 0;
  aiPolishStatus.value = "正在润色内容...";
  aiPolishText.value = "";
  aiComparison.original.title = form.title;
  aiComparison.original.tags = form.tags;
  aiComparison.original.content = form.content;
  aiComparison.polished.title = "";
  aiComparison.polished.tags = "";
  aiComparison.polished.content = "";
  aiComparison.selected.title = "original";
  aiComparison.selected.tags = "original";
  aiComparison.selected.content = "original";

  try {
    await streamRequest({
      path: "/ai/polish-post/stream/",
      body: {
        title: form.title,
        content: form.content,
        tags: form.tags,
      },
      onEvent: (event, data) => {
        if (event === "progress") {
          aiPolishProgress.value = data.progress || 0;
          aiPolishStatus.value = data.message || "";
        }
        if (event === "content") {
          aiPolishText.value = data.content || "";
        }
        if (event === "done") {
          aiPolishText.value = data.content || aiPolishText.value;
          aiPolishProgress.value = 100;
          aiPolishStatus.value = "润色完成";
        }
        if (event === "error") {
          aiPolishStatus.value = data.detail || "AI 润色失败";
        }
      },
    });

    const text = aiPolishText.value || "";
    const titleMatch = text.match(/标题[:：]\s*(.*)/);
    const contentMatch = text.match(/正文[:：]\s*([\s\S]*?)标签建议[:：]/);
    const tagsMatch = text.match(/标签建议[:：]\s*(.*)/);

    aiComparison.polished.title = titleMatch ? titleMatch[1].trim() : aiComparison.original.title;
    aiComparison.polished.content = contentMatch ? contentMatch[1].trim() : aiComparison.original.content;
    aiComparison.polished.tags = tagsMatch ? tagsMatch[1].trim() : aiComparison.original.tags;
    aiComparison.selected.title = aiComparison.polished.title && aiComparison.polished.title !== aiComparison.original.title ? "polished" : "original";
    aiComparison.selected.tags = aiComparison.polished.tags && aiComparison.polished.tags !== aiComparison.original.tags ? "polished" : "original";
    aiComparison.selected.content =
      aiComparison.polished.content && aiComparison.polished.content !== aiComparison.original.content ? "polished" : "original";
    applySelectedPolish();
  } catch (error) {
    aiPolishStatus.value = error.message || "AI 润色失败";
  } finally {
    aiPolishLoading.value = false;
  }
};

const toggleLike = async (postId) => {
  await http.post(`/social/posts/${postId}/like/`);
  await fetchPosts();
};

const toggleFavoritePost = (post) => {
  favoritePostIds.value = toggleFavoriteId(postFavoriteStorageKey, post.id);
  uiStore.pushToast(isPostFavorite(post.id) ? `已收藏《${post.title}》` : `已取消收藏《${post.title}》`, "success");
};

const sharePost = async (post) => {
  await shareContent({
    title: post.title,
    path: `/community/${post.id}`,
    summary: post.content_preview,
    onSuccess: () => uiStore.pushToast("分享链接已准备好", "success"),
    onError: () => uiStore.pushToast("分享失败，请稍后再试"),
  });
};

const openCommentModal = (postId) => {
  activePostId.value = postId;
  commentModalOpen.value = true;
};

const openReplyModal = (postId, commentId) => {
  activePostId.value = postId;
  activeCommentId.value = commentId;
  replyModalOpen.value = true;
};

const submitComment = async (postId, parentId = null) => {
  const source = parentId ? replyDrafts : commentDrafts;
  const content = source[parentId || postId];
  if (!content) return;
  await http.post(`/social/posts/${postId}/comments/`, {
    content,
    parent: parentId,
  });
  source[parentId || postId] = "";
  if (parentId) {
    replyModalOpen.value = false;
    activeCommentId.value = null;
  } else {
    commentModalOpen.value = false;
  }
  activePostId.value = null;
  await fetchPosts();
};

onMounted(async () => {
  favoritePostIds.value = getFavoriteIds(postFavoriteStorageKey);
  await Promise.all([fetchPosts(), fetchDestinations()]);
});
</script>

<template>
  <section class="panel community-hero">
    <div class="split community-hero-head">
      <div>
        <p class="eyebrow">社区动态</p>
        <h3>围绕景点、路线和真实体验展开交流</h3>
        <p class="muted">分享旅行故事、点赞互动、参与评论，让平台里的每一段旅程都更有温度。</p>
      </div>
      <button class="btn btn-primary btn-compact" :disabled="!authStore.isAuthenticated" @click="postModalOpen = true">
        发布旅行故事
      </button>
    </div>
  </section>

  <section class="panel">
    <div class="filter-bar">
      <select v-model="feedFilter.destination" class="select">
        <option value="all">全部景点</option>
        <option v-for="item in destinations" :key="item.id" :value="String(item.id)">{{ item.name }}</option>
      </select>
      <select v-model="feedFilter.sort" class="select">
        <option value="latest">最新发布</option>
        <option value="hot">热度优先</option>
        <option value="comments">评论最多</option>
      </select>
    </div>
  </section>

  <section class="community-feed">
    <article v-if="loading" v-for="item in skeletonPosts" :key="`skeleton-${item.id}`" class="card feed-card skeleton-card">
      <div class="skeleton-line skeleton-line-title"></div>
      <div class="skeleton-line skeleton-line-subtitle"></div>
      <div class="skeleton-media"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-actions">
        <span class="skeleton-chip"></span>
        <span class="skeleton-chip"></span>
        <span class="skeleton-chip"></span>
      </div>
    </article>

    <div v-else-if="!filteredPosts.length" class="card empty-state-card">
      <div class="empty-state-illustration review-empty-art"></div>
      <h3>当前筛选下暂无帖子</h3>
      <p class="muted">可以切换景点或排序方式，也可以自己发布一篇新的旅行故事。</p>
    </div>

    <article v-else v-for="post in filteredPosts" :key="post.id" class="card feed-card interactive-card">
      <div class="feed-card-top">
        <div class="post-author">
          <img v-if="post.author_avatar" :src="post.author_avatar" alt="author avatar" class="author-avatar" />
          <div>
            <h3>{{ post.title }}</h3>
            <p class="muted">{{ post.author_name }} · {{ post.destination_name || "未关联景点" }}</p>
          </div>
          <span class="pill">{{ post.like_count }} 赞</span>
        </div>
      </div>

      <img v-if="post.cover" :src="post.cover" :alt="post.title" class="cover feed-cover" />

      <div class="feed-summary">
        <p class="summary-two-lines">{{ post.content_preview }}</p>
      </div>

      <div class="action-row feed-actions">
        <RouterLink :to="`/community/${post.id}`" class="btn btn-secondary">查看详情</RouterLink>
        <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated" @click="toggleLike(post.id)">
          {{ post.current_user_liked ? "取消点赞" : "点赞" }}
        </button>
        <button class="btn btn-secondary" @click="toggleFavoritePost(post)">
          {{ isPostFavorite(post.id) ? "取消收藏" : "收藏" }}
        </button>
        <button class="btn btn-secondary" @click="sharePost(post)">分享</button>
        <button class="btn btn-primary" :disabled="!authStore.isAuthenticated" @click="openCommentModal(post.id)">评论</button>
      </div>
    </article>
  </section>

  <div v-if="postModalOpen" class="modal-backdrop" @click.self="postModalOpen = false">
    <div class="modal-card">
      <div class="split">
        <h3>发布旅行故事</h3>
        <button class="btn btn-secondary" @click="postModalOpen = false">关闭</button>
      </div>
      <div class="form-grid">
        <input v-model="form.title" class="input" placeholder="标题" />
        <select v-model="form.destination" class="select">
          <option value="">关联景点</option>
          <option v-for="item in destinations" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <img v-if="coverPreview" :src="coverPreview" alt="封面预览" class="cover" />
        <input v-model="form.cover" class="input" placeholder="封面图片引用" />
        <input class="input" type="file" accept="image/*" @change="uploadCover" />
        <input v-model="form.tags" class="input" placeholder="标签，例如：海边,自驾,日落" />
        <textarea v-model="form.content" class="textarea" placeholder="写下你的路线、花费、体验和建议"></textarea>

        <div v-if="aiPolishLoading || aiPolishText || aiPolishStatus" class="stream-box">
          <div class="stream-head">
            <strong>AI 润色进度</strong>
            <span>{{ aiPolishProgress }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-bar" :style="{ width: `${aiPolishProgress}%` }"></div>
          </div>
          <p class="muted">{{ aiPolishStatus }}</p>
          <div v-if="aiPolishText && aiPolishProgress < 100" class="card">
            <MarkdownContent :content="aiPolishText" />
          </div>
        </div>

        <div v-if="aiComparison.polished.title || aiComparison.polished.tags || aiComparison.polished.content" class="form-grid">
          <div class="compare-grid">
            <div class="card">
              <p class="eyebrow">标题对比</p>
              <p><strong>润色前：</strong>{{ aiComparison.original.title || "未填写" }}</p>
              <p><strong>润色后：</strong>{{ aiComparison.polished.title || "未生成" }}</p>
              <div class="action-row">
                <button
                  class="btn"
                  :class="aiComparison.selected.title === 'original' ? 'btn-secondary' : 'btn-primary'"
                  @click="aiComparison.selected.title = 'original'; applySelectedPolish()"
                >
                  使用润色前
                </button>
                <button
                  class="btn"
                  :class="aiComparison.selected.title === 'polished' ? 'btn-secondary' : 'btn-primary'"
                  @click="aiComparison.selected.title = 'polished'; applySelectedPolish()"
                >
                  使用润色后
                </button>
              </div>
            </div>

            <div class="card">
              <p class="eyebrow">标签对比</p>
              <p><strong>润色前：</strong>{{ aiComparison.original.tags || "未填写" }}</p>
              <p><strong>润色后：</strong>{{ aiComparison.polished.tags || "未生成" }}</p>
              <div class="action-row">
                <button
                  class="btn"
                  :class="aiComparison.selected.tags === 'original' ? 'btn-secondary' : 'btn-primary'"
                  @click="aiComparison.selected.tags = 'original'; applySelectedPolish()"
                >
                  使用润色前
                </button>
                <button
                  class="btn"
                  :class="aiComparison.selected.tags === 'polished' ? 'btn-secondary' : 'btn-primary'"
                  @click="aiComparison.selected.tags = 'polished'; applySelectedPolish()"
                >
                  使用润色后
                </button>
              </div>
            </div>
          </div>

          <div class="card">
            <p class="eyebrow">正文对比</p>
            <div class="compare-grid">
              <div class="card compare-card-inner">
                <p><strong>润色前</strong></p>
                <MarkdownContent :content="aiComparison.original.content || '未填写'" />
              </div>
              <div class="card compare-card-inner">
                <p><strong>润色后</strong></p>
                <MarkdownContent :content="aiComparison.polished.content || '未生成'" />
              </div>
            </div>
            <div class="action-row">
              <button
                class="btn"
                :class="aiComparison.selected.content === 'original' ? 'btn-secondary' : 'btn-primary'"
                @click="aiComparison.selected.content = 'original'; applySelectedPolish()"
              >
                正文使用润色前
              </button>
              <button
                class="btn"
                :class="aiComparison.selected.content === 'polished' ? 'btn-secondary' : 'btn-primary'"
                @click="aiComparison.selected.content = 'polished'; applySelectedPolish()"
              >
                正文使用润色后
              </button>
            </div>
          </div>
        </div>

        <div class="action-row">
          <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated || aiPolishLoading" @click="polishPost">
            {{ aiPolishLoading ? "润色中..." : "AI 润色内容" }}
          </button>
          <button class="btn btn-primary" @click="submitPost">提交发布</button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="commentModalOpen" class="modal-backdrop" @click.self="commentModalOpen = false">
    <div class="modal-card">
      <div class="split">
        <h3>发表评论</h3>
        <button class="btn btn-secondary" @click="commentModalOpen = false">关闭</button>
      </div>
      <div class="form-grid">
        <textarea v-model="commentDrafts[activePostId]" class="textarea" placeholder="写下你的评论"></textarea>
        <button class="btn btn-primary" @click="submitComment(activePostId)">提交评论</button>
      </div>
    </div>
  </div>

  <div v-if="replyModalOpen" class="modal-backdrop" @click.self="replyModalOpen = false">
    <div class="modal-card">
      <div class="split">
        <h3>回复评论</h3>
        <button class="btn btn-secondary" @click="replyModalOpen = false">关闭</button>
      </div>
      <div class="form-grid">
        <textarea v-model="replyDrafts[activeCommentId]" class="textarea" placeholder="写下你的回复"></textarea>
        <button class="btn btn-primary" @click="submitComment(activePostId, activeCommentId)">提交回复</button>
      </div>
    </div>
  </div>
</template>
