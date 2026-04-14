<script setup>
import { onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const posts = ref([]);
const destinations = ref([]);
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
const aiPolishLoading = ref(false);
const aiPolishProgress = ref(0);
const aiPolishStatus = ref("");
const aiPolishText = ref("");
const aiComparison = reactive({
  original: {
    title: "",
    tags: "",
    content: "",
  },
  polished: {
    title: "",
    tags: "",
    content: "",
  },
  selected: {
    title: "original",
    tags: "original",
    content: "original",
  },
});

const fetchPosts = async () => {
  const { data } = await http.get("/social/posts/");
  posts.value = data.results ?? data;
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
  form.tags =
    aiComparison.selected.tags === "polished" ? aiComparison.polished.tags || aiComparison.original.tags : aiComparison.original.tags;
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
  await Promise.all([fetchPosts(), fetchDestinations()]);
});
</script>

<template>
  <section class="panel">
    <div class="split">
      <div>
        <p class="eyebrow">社区动态</p>
        <p class="muted">分享真实旅途体验，围绕景点、路线和玩法展开互动。</p>
      </div>
      <button class="btn btn-primary btn-compact" :disabled="!authStore.isAuthenticated" @click="postModalOpen = true">
        发布旅行故事
      </button>
    </div>

    <div class="form-grid" style="margin-top: 16px;">
      <article v-for="post in posts" :key="post.id" class="card">
        <img v-if="post.cover" :src="post.cover" :alt="post.title" class="cover" />
        <div class="post-author">
          <img v-if="post.author_avatar" :src="post.author_avatar" alt="author avatar" class="author-avatar" />
          <div>
            <h3>{{ post.title }}</h3>
            <p class="muted">{{ post.author_name }} · {{ post.destination_name || "未关联景点" }}</p>
          </div>
          <span class="pill">{{ post.like_count }} 赞</span>
        </div>
        <p class="summary-two-lines">{{ post.content_preview }}</p>
        <div class="action-row">
          <RouterLink :to="`/community/${post.id}`" class="btn btn-secondary">查看详情</RouterLink>
          <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated" @click="toggleLike(post.id)">点赞</button>
          <button class="btn btn-primary" :disabled="!authStore.isAuthenticated" @click="openCommentModal(post.id)">评论</button>
        </div>
      </article>
    </div>
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
        <div
          v-if="aiComparison.polished.title || aiComparison.polished.tags || aiComparison.polished.content"
          class="form-grid"
        >
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
