<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";

import MarkdownContent from "../components/MarkdownContent.vue";
import http from "../api/http";
import { streamRequest } from "../api/stream";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const authStore = useAuthStore();

const post = ref(null);
const loading = ref(false);
const commentLoading = ref(false);
const commentDraft = ref("");
const destinations = ref([]);
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

const fetchPost = async () => {
  loading.value = true;
  try {
    const { data } = await http.get(`/social/posts/${route.params.id}/`);
    post.value = data;
    syncEditForm();
    detectCoverLayout(data.cover);
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
</script>

<template>
  <section v-if="post" class="page">
    <article class="panel">
      <p class="eyebrow">帖子详情</p>
      <div class="post-author">
        <div class="comment-line">
          <img v-if="post.author_avatar" :src="post.author_avatar" alt="avatar" class="author-avatar" />
          <div>
            <h3>{{ post.title }}</h3>
            <p class="muted">{{ post.author_name }} · {{ post.destination_name || "未关联景点" }}</p>
          </div>
        </div>
        <span class="pill">{{ post.like_count }} 赞 · {{ post.comment_count }} 评</span>
      </div>
      <div class="tag-row" v-if="post.tags">
        <span v-for="tag in post.tags.split(',').filter(Boolean)" :key="tag" class="tag">{{ tag.trim() }}</span>
      </div>

      <div :class="['post-detail-main', { 'post-detail-main-side': isSideLayout }]" style="margin-top: 16px;">
        <div v-if="post.cover" class="post-detail-media">
          <img :src="post.cover" :alt="post.title" class="post-detail-cover" />
        </div>
        <div class="card post-detail-text">
          <MarkdownContent :content="post.content" />
        </div>
      </div>

      <div class="action-row" style="margin-top: 16px;">
        <button v-if="canEdit" class="btn btn-secondary" @click="editModalOpen = true">编辑重新发布</button>
      </div>
    </article>

    <article class="panel">
      <div class="split">
        <div>
          <p class="eyebrow">AI 总结</p>
          <h3>一键总结帖子内容与评论重点</h3>
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
        <div v-if="summaryText" class="card">
          <MarkdownContent :content="summaryText" />
        </div>
      </div>
    </article>

    <article class="panel">
      <p class="eyebrow">全部评论</p>
      <div class="form-grid">
        <div v-if="!post?.comments?.length" class="card muted">当前还没有评论，欢迎留下第一条交流内容。</div>
        <div v-for="comment in post?.comments || []" :key="comment.id" class="card">
          <div class="comment-line">
            <img v-if="comment.author_avatar" :src="comment.author_avatar" alt="comment avatar" class="author-avatar small-avatar" />
            <div>
              <strong>{{ comment.author_name }}</strong>
              <p>{{ comment.content }}</p>
              <p class="muted">{{ comment.created_at }}</p>
            </div>
          </div>
          <div v-if="comment.replies?.length" class="form-grid" style="margin-top: 12px;">
            <div v-for="reply in comment.replies" :key="reply.id" class="comment-line">
              <img v-if="reply.author_avatar" :src="reply.author_avatar" alt="reply avatar" class="author-avatar small-avatar" />
              <div>
                <strong>{{ reply.author_name }}</strong>
                <p class="muted">{{ reply.content }}</p>
                <p class="muted">{{ reply.created_at }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </article>

    <article class="panel">
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

  <section v-if="loading" class="panel">
    <p class="muted">正在加载帖子详情...</p>
  </section>
</template>
