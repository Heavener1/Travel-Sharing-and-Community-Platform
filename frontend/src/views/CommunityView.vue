<script setup>
import { onMounted, reactive, ref } from "vue";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const posts = ref([]);
const destinations = ref([]);
const aiProviders = ref({});
const form = reactive({
  title: "",
  content: "",
  cover: "",
  destination: "",
  tags: "",
});
const aiForm = reactive({
  provider: "qwen",
  model: "",
});
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

const fetchPosts = async () => {
  const { data } = await http.get("/social/posts/");
  posts.value = data.results ?? data;
};

const fetchDestinations = async () => {
  const { data } = await http.get("/travel/destinations/");
  destinations.value = data.results ?? data;
};

const fetchAIProviders = async () => {
  if (!authStore.isAuthenticated) return;
  const { data } = await http.get("/ai/providers/");
  aiProviders.value = data;
  if (data[aiForm.provider] && !aiForm.model) {
    aiForm.model = data[aiForm.provider].default_model;
  }
};

const submitPost = async () => {
  await http.post("/social/posts/", form);
  form.title = "";
  form.content = "";
  form.cover = "";
  form.destination = "";
  form.tags = "";
  aiPolishText.value = "";
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
};

const polishPost = async () => {
  aiPolishLoading.value = true;
  aiPolishProgress.value = 0;
  aiPolishStatus.value = "准备润色内容...";
  aiPolishText.value = "";
  try {
    await streamRequest({
      path: "/ai/polish-post/stream/",
      body: {
        provider: aiForm.provider,
        model: aiForm.model || undefined,
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
    const titleMatch = text.match(/标题[:：](.*)/);
    const contentMatch = text.match(/正文[:：]([\s\S]*?)标签建议[:：]/);
    const tagsMatch = text.match(/标签建议[:：](.*)/);
    if (titleMatch) form.title = titleMatch[1].trim();
    if (contentMatch) form.content = contentMatch[1].trim();
    if (tagsMatch) form.tags = tagsMatch[1].trim();
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
  await Promise.all([fetchPosts(), fetchDestinations(), fetchAIProviders()]);
});
</script>

<template>
  <section class="panel">
    <div class="split">
      <div>
        <p class="eyebrow">社区动态</p>
        <p class="muted">分享真实旅途体验，围绕目的地和路线展开互动。</p>
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
            <p class="muted">{{ post.author_name }} · {{ post.destination_name || "未关联目的地" }}</p>
          </div>
          <span class="pill">{{ post.status === "approved" ? `${post.like_count} 赞` : "待审核" }}</span>
        </div>
        <p>{{ post.content }}</p>
        <p v-if="post.review_note" class="muted">审核备注：{{ post.review_note }}</p>
        <div class="action-row">
          <button class="btn btn-secondary" :disabled="!authStore.isAuthenticated" @click="toggleLike(post.id)">点赞</button>
          <button class="btn btn-primary" :disabled="!authStore.isAuthenticated" @click="openCommentModal(post.id)">评论</button>
        </div>
        <div class="form-grid" v-if="post.comments?.length">
          <div v-for="comment in post.comments" :key="comment.id" class="panel">
            <div class="comment-line">
              <img v-if="comment.author_avatar" :src="comment.author_avatar" alt="comment avatar" class="author-avatar small-avatar" />
              <p><strong>{{ comment.author_name }}</strong>：{{ comment.content }}</p>
            </div>
            <div v-if="comment.replies?.length" class="form-grid">
              <div v-for="reply in comment.replies" :key="reply.id" class="comment-line">
                <img v-if="reply.author_avatar" :src="reply.author_avatar" alt="reply avatar" class="author-avatar small-avatar" />
                <p class="muted">{{ reply.author_name }} 回复：{{ reply.content }}</p>
              </div>
            </div>
            <div class="action-row">
              <button class="btn btn-primary" :disabled="!authStore.isAuthenticated" @click="openReplyModal(post.id, comment.id)">回复</button>
            </div>
          </div>
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
          <option value="">关联目的地</option>
          <option v-for="item in destinations" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <input v-model="form.cover" class="input" placeholder="封面图片引用" />
        <input class="input" type="file" accept="image/*" @change="uploadCover" />
        <input v-model="form.tags" class="input" placeholder="标签，例如：海岛,自驾,日落" />
        <textarea v-model="form.content" class="textarea" placeholder="写下你的路线、花费、体验和建议"></textarea>
        <div class="grid-3">
          <select v-model="aiForm.provider" class="select" @change="aiForm.model = aiProviders[aiForm.provider]?.default_model || ''">
            <option value="qwen">千问</option>
            <option value="kimi">Kimi</option>
          </select>
          <select v-model="aiForm.model" class="select">
            <option v-for="item in (aiProviders[aiForm.provider]?.models || [])" :key="item" :value="item">
              {{ item }}
            </option>
          </select>
          <input v-model="aiForm.model" class="input" placeholder="也可以手动输入模型名" />
        </div>
        <div v-if="aiPolishLoading || aiPolishText || aiPolishStatus" class="stream-box">
          <div class="stream-head">
            <strong>AI 润色进度</strong>
            <span>{{ aiPolishProgress }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-bar" :style="{ width: `${aiPolishProgress}%` }"></div>
          </div>
          <p class="muted">{{ aiPolishStatus }}</p>
          <div v-if="aiPolishText" class="card">
            <MarkdownContent :content="aiPolishText" />
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
