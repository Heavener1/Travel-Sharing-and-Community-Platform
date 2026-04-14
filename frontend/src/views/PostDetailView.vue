<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import MarkdownContent from "../components/MarkdownContent.vue";
import { useReadingProgress } from "../composables/useReadingProgress";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();
const { readingProgress } = useReadingProgress();

const post = ref(null);
const loading = ref(false);
const commentLoading = ref(false);
const commentDraft = ref("");
const replyModalOpen = ref(false);
const replyLoading = ref(false);
const replyDraft = ref("");
const activeCommentId = ref(null);
const destinations = ref([]);
const allRelatedPosts = ref([]);
const allRelatedDestinations = ref([]);
const relatedBatchIndex = ref(0);
const relatedLoading = ref(false);
const editModalOpen = ref(false);
const editLoading = ref(false);
const editForm = reactive({
  title: "",
  content: "",
  cover: "",
  destination: "",
  tags: "",
});
const editCoverPreview = ref("");
const summaryLoading = ref(false);
const summaryProgress = ref(0);
const summaryStatus = ref("");
const summaryText = ref("");
const coverLayout = ref("stack");

const canEdit = computed(() => authStore.isAuthenticated && post.value?.author === authStore.user?.id);
const isSideLayout = computed(() => coverLayout.value === "side");

const relatedPosts = computed(() => {
  const list = allRelatedPosts.value;
  if (!list.length) return [];
  const start = (relatedBatchIndex.value * 4) % list.length;
  return Array.from({ length: Math.min(4, list.length) }, (_, index) => list[(start + index) % list.length]);
});

const relatedDestinations = computed(() => {
  const list = allRelatedDestinations.value;
  if (!list.length) return [];
  const start = (relatedBatchIndex.value * 3) % list.length;
  return Array.from({ length: Math.min(3, list.length) }, (_, index) => list[(start + index) % list.length]);
});

const scrollToSection = (id) => {
  const element = document.getElementById(id);
  if (element) {
    element.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};

const backToTop = () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const nextRelatedBatch = () => {
  relatedBatchIndex.value += 1;
};

const detectCoverLayout = (coverUrl) => {
  if (!coverUrl) {
    coverLayout.value = "stack";
    return;
  }
  const image = new Image();
  image.onload = () => {
    coverLayout.value = image.naturalWidth > image.naturalHeight ? "stack" : "side";
  };
  image.onerror = () => {
    coverLayout.value = "stack";
  };
  image.src = coverUrl;
};

const syncEditForm = () => {
  if (!post.value) return;
  editForm.title = post.value.title || "";
  editForm.content = post.value.content || "";
  editForm.cover = post.value.cover_reference || "";
  editForm.destination = post.value.destination || "";
  editForm.tags = post.value.tags || "";
  editCoverPreview.value = post.value.cover || "";
};

const fetchRelatedContent = async (postId) => {
  relatedLoading.value = true;
  try {
    const { data } = await http.get(`/social/posts/${postId}/related/`);
    allRelatedPosts.value = data.related_posts || [];
    allRelatedDestinations.value = data.related_destinations || [];
    relatedBatchIndex.value = 0;
  } finally {
    relatedLoading.value = false;
  }
};

const fetchPost = async () => {
  loading.value = true;
  try {
    const { data } = await http.get(`/social/posts/${route.params.id}/`);
    post.value = data;
    syncEditForm();
    detectCoverLayout(data.cover);
    await fetchRelatedContent(data.id);
  } finally {
    loading.value = false;
  }
};

const fetchDestinations = async () => {
  const { data } = await http.get("/travel/destinations/");
  destinations.value = data.results ?? data;
};

const uploadCover = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  const payload = new FormData();
  payload.append("file", file);
  const { data } = await http.post("/travel/upload/", payload, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  editForm.cover = data.reference || data.url;
  editCoverPreview.value = data.url || data.reference || "";
  event.target.value = "";
};

const savePost = async () => {
  editLoading.value = true;
  try {
    const payload = {
      title: editForm.title,
      content: editForm.content,
      cover: editForm.cover,
      destination: editForm.destination || null,
      tags: editForm.tags,
    };
    const { data } = await http.patch(`/social/posts/${route.params.id}/`, payload);
    post.value = data;
    editCoverPreview.value = data.cover || "";
    editForm.cover = data.cover_reference || "";
    detectCoverLayout(data.cover);
    await fetchRelatedContent(data.id);
    editModalOpen.value = false;
  } finally {
    editLoading.value = false;
  }
};

const submitComment = async () => {
  if (!commentDraft.value.trim()) return;
  commentLoading.value = true;
  try {
    await http.post(`/social/posts/${route.params.id}/comments/`, {
      content: commentDraft.value,
    });
    commentDraft.value = "";
    await fetchPost();
  } finally {
    commentLoading.value = false;
  }
};

const toggleLike = async () => {
  if (!authStore.isAuthenticated) return;
  await http.post(`/social/posts/${route.params.id}/like/`);
  await fetchPost();
};

const openReplyModal = (commentId) => {
  activeCommentId.value = commentId;
  replyDraft.value = "";
  replyModalOpen.value = true;
};

const submitReply = async () => {
  if (!replyDraft.value.trim() || !activeCommentId.value) return;
  replyLoading.value = true;
  try {
    await http.post(`/social/posts/${route.params.id}/comments/`, {
      content: replyDraft.value,
      parent: activeCommentId.value,
    });
    replyDraft.value = "";
    replyModalOpen.value = false;
    activeCommentId.value = null;
    await fetchPost();
  } finally {
    replyLoading.value = false;
  }
};

const summarizePost = async () => {
  summaryLoading.value = true;
  summaryProgress.value = 0;
  summaryStatus.value = "正在整理帖子与评论内容...";
  summaryText.value = "";
  try {
    await streamRequest({
      path: "/ai/post-summary/stream/",
      body: {
        post_id: Number(route.params.id),
      },
      onEvent: (event, data) => {
        if (event === "progress") {
          summaryProgress.value = data.progress || 0;
          summaryStatus.value = data.message || "";
        }
        if (event === "content") {
          summaryText.value = data.content || "";
        }
        if (event === "done") {
          summaryText.value = data.content || summaryText.value;
          summaryProgress.value = 100;
          summaryStatus.value = "总结完成";
        }
        if (event === "error") {
          summaryStatus.value = data.detail || "AI 总结失败";
        }
      },
    });
  } catch (error) {
    summaryStatus.value = error.message || "AI 总结失败";
  } finally {
    summaryLoading.value = false;
  }
};

onMounted(async () => {
  await Promise.all([fetchPost(), fetchDestinations()]);
});

watch(
  () => route.params.id,
  async () => {
    await fetchPost();
  },
);
</script>

<template>
  <section v-if="post" class="page post-detail-page">
    <div class="reading-progress">
      <div class="reading-progress-bar" :style="{ width: `${readingProgress}%` }"></div>
    </div>

    <div class="detail-sticky-bar">
      <div class="filter-bar filter-bar-tight">
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('post-overview')">帖子正文</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('post-summary')">AI 总结</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('post-comments')">全部评论</button>
        <button class="btn btn-secondary btn-compact" @click="scrollToSection('post-discuss')">参与讨论</button>
        <button class="btn theme-toggle-btn btn-compact" @click="backToTop">返回顶部</button>
      </div>
    </div>

    <article id="post-overview" class="panel post-detail-shell">
      <div class="post-detail-header">
        <div class="post-author">
          <div class="comment-line">
            <img v-if="post.author_avatar" :src="post.author_avatar" alt="avatar" class="author-avatar" />
            <div>
              <p class="eyebrow">帖子详情</p>
              <h2 class="post-detail-title">{{ post.title }}</h2>
              <p class="muted">{{ post.author_name }} · {{ post.destination_name || "未关联景点" }}</p>
            </div>
          </div>
          <span class="pill">{{ post.like_count }} 赞 · {{ post.comment_count }} 评</span>
        </div>

        <div class="tag-row" v-if="post.tags">
          <span v-for="tag in post.tags.split(',').filter(Boolean)" :key="tag" class="tag">{{ tag.trim() }}</span>
        </div>
      </div>

      <div :class="['post-detail-main', { 'post-detail-main-side': isSideLayout }]" style="margin-top: 18px;">
        <div v-if="post.cover" class="post-detail-media post-detail-hero-media">
          <img :src="post.cover" :alt="post.title" class="post-detail-cover" />
        </div>
        <div class="card post-detail-text markdown-wrap">
          <MarkdownContent :content="post.content" />
        </div>
      </div>

      <div class="action-row post-detail-actions">
        <button class="btn btn-primary" :disabled="!authStore.isAuthenticated" @click="toggleLike">
          {{ post.current_user_liked ? "取消点赞" : "点赞" }}
        </button>
        <button v-if="canEdit" class="btn btn-secondary" @click="editModalOpen = true">编辑重新发布</button>
      </div>
    </article>

    <article id="post-summary" class="panel post-detail-summary">
      <div class="split">
        <div>
          <p class="eyebrow">AI 总结</p>
          <h3>一键提炼帖子内容和评论重点</h3>
        </div>
        <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated || summaryLoading" @click="summarizePost">
          {{ summaryLoading ? "总结中..." : "AI 一键总结" }}
        </button>
      </div>
      <div v-if="summaryLoading || summaryText || summaryStatus" class="stream-box" style="margin-top: 16px;">
        <div class="stream-head">
          <strong>总结进度</strong>
          <span>{{ summaryProgress }}%</span>
        </div>
        <div class="progress-track">
          <div class="progress-bar" :style="{ width: `${summaryProgress}%` }"></div>
        </div>
        <p class="muted">{{ summaryStatus }}</p>
        <div v-if="summaryText" class="card markdown-wrap">
          <MarkdownContent :content="summaryText" />
        </div>
      </div>
    </article>

    <article class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">相关推荐</p>
          <h3>继续延展这篇内容相关的阅读路径</h3>
        </div>
        <button class="btn btn-secondary btn-compact" :disabled="!allRelatedPosts.length && !allRelatedDestinations.length" @click="nextRelatedBatch">
          换一批
        </button>
      </div>
      <section class="grid-2 related-grid" style="margin-top: 16px;">
        <div class="card">
          <p class="eyebrow">相似帖子</p>
          <div v-if="relatedLoading" class="muted">正在整理相关推荐...</div>
          <div v-else-if="!relatedPosts.length" class="muted">暂时还没有匹配到更相关的帖子。</div>
          <div v-else class="form-grid">
            <RouterLink v-for="item in relatedPosts" :key="item.id" :to="`/community/${item.id}`" class="card related-link-card">
              <strong>{{ item.title }}</strong>
              <p class="muted">{{ item.author_name }} · {{ item.destination_name || "未关联景点" }}</p>
            </RouterLink>
          </div>
        </div>

        <div class="card">
          <p class="eyebrow">关联景点</p>
          <div v-if="relatedLoading" class="muted">正在整理相关推荐...</div>
          <div v-else-if="!relatedDestinations.length" class="muted">暂时还没有关联景点推荐。</div>
          <div v-else class="form-grid">
            <RouterLink v-for="item in relatedDestinations" :key="item.id" :to="`/explore/${item.id}`" class="card related-link-card">
              <strong>{{ item.name }}</strong>
              <p class="muted">{{ item.city }} · {{ item.province }}</p>
            </RouterLink>
          </div>
        </div>
      </section>
    </article>

    <section class="grid-2 post-discussion-grid">
      <article id="post-comments" class="panel">
        <p class="eyebrow">全部评论</p>
        <div class="form-grid">
          <div v-if="!post?.comments?.length" class="card muted">当前还没有评论，欢迎留下第一条交流内容。</div>
          <div v-for="comment in post?.comments || []" :key="comment.id" class="card comment-card">
            <div class="comment-line">
              <img v-if="comment.author_avatar" :src="comment.author_avatar" alt="comment avatar" class="author-avatar small-avatar" />
              <div class="comment-copy">
                <strong>{{ comment.author_name }}</strong>
                <p>{{ comment.content }}</p>
                <p class="muted">{{ comment.created_at }}</p>
              </div>
            </div>
            <div class="action-row" style="margin-top: 12px;">
              <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated" @click="openReplyModal(comment.id)">回复</button>
            </div>
            <div v-if="comment.replies?.length" class="form-grid reply-list" style="margin-top: 14px;">
              <div v-for="reply in comment.replies" :key="reply.id" class="comment-line reply-card">
                <img v-if="reply.author_avatar" :src="reply.author_avatar" alt="reply avatar" class="author-avatar small-avatar" />
                <div class="comment-copy">
                  <strong>{{ reply.author_name }}</strong>
                  <p class="muted">{{ reply.content }}</p>
                  <p class="muted">{{ reply.created_at }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article id="post-discuss" class="panel discussion-panel">
        <p class="eyebrow">参与讨论</p>
        <div class="form-grid">
          <textarea
            v-model="commentDraft"
            class="textarea"
            :placeholder="authStore.isAuthenticated ? '写下你对这篇旅行故事的想法' : '登录后可发表评论'"
            :disabled="!authStore.isAuthenticated || commentLoading"
          ></textarea>
          <button class="btn btn-primary" :disabled="!authStore.isAuthenticated || commentLoading" @click="submitComment">
            {{ commentLoading ? "提交中..." : "发布评论" }}
          </button>
        </div>
      </article>
    </section>
  </section>

  <div v-if="editModalOpen" class="modal-backdrop" @click.self="editModalOpen = false">
    <div class="modal-card">
      <div class="split">
        <h3>编辑帖子并重新发布</h3>
        <button class="btn btn-secondary" @click="editModalOpen = false">关闭</button>
      </div>
      <div class="form-grid">
        <input v-model="editForm.title" class="input" placeholder="标题" />
        <select v-model="editForm.destination" class="select">
          <option value="">关联景点</option>
          <option v-for="item in destinations" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <img v-if="editCoverPreview" :src="editCoverPreview" alt="封面预览" class="cover" />
        <input v-model="editForm.cover" class="input" placeholder="封面图片引用" />
        <input class="input" type="file" accept="image/*" @change="uploadCover" />
        <input v-model="editForm.tags" class="input" placeholder="标签，例如：海边,自驾,日落" />
        <textarea v-model="editForm.content" class="textarea" placeholder="更新你的旅行故事内容"></textarea>
        <button class="btn btn-primary" :disabled="editLoading" @click="savePost">
          {{ editLoading ? "重新发布中..." : "保存并重新发布" }}
        </button>
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
        <textarea v-model="replyDraft" class="textarea" placeholder="写下你的回复" :disabled="replyLoading"></textarea>
        <button class="btn btn-primary" :disabled="replyLoading" @click="submitReply">
          {{ replyLoading ? "提交中..." : "提交回复" }}
        </button>
      </div>
    </div>
  </div>

  <section v-if="loading" class="page">
    <article class="panel skeleton-card">
      <div class="skeleton-line skeleton-line-title"></div>
      <div class="skeleton-line skeleton-line-subtitle"></div>
      <div class="skeleton-media skeleton-media-large"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line"></div>
      <div class="skeleton-line skeleton-line-short"></div>
    </article>
  </section>
</template>
