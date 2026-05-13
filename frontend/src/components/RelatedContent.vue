<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";

const props = defineProps({
  relatedDestinations: { type: Array, default: () => [] },
  relatedPosts: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  title: { type: String, required: true },
  variant: {
    type: String,
    default: "post",
    validator: (v) => ["post", "scenic"].includes(v),
  },
});

defineEmits(["next-batch"]);

const isPostVariant = computed(() => props.variant === "post");

const leftLabel = computed(() => (isPostVariant.value ? "相似帖子" : "相似景点"));
const rightLabel = computed(() => (isPostVariant.value ? "关联景点" : "相关帖子"));

const leftItems = computed(() =>
  isPostVariant.value ? props.relatedPosts : props.relatedDestinations,
);
const rightItems = computed(() =>
  isPostVariant.value ? props.relatedDestinations : props.relatedPosts,
);

const leftEmptyMessage = computed(() =>
  isPostVariant.value
    ? "暂时还没有匹配到更相关的帖子。"
    : "暂时还没有匹配到相似景点。",
);
const rightEmptyMessage = computed(() =>
  isPostVariant.value
    ? "暂时还没有关联景点推荐。"
    : "暂时还没有关联的旅行故事。",
);

const hasAnyContent = computed(
  () => props.relatedPosts.length || props.relatedDestinations.length,
);
</script>

<template>
  <article class="panel">
    <div class="split">
      <div>
        <p class="eyebrow">相关推荐</p>
        <h3>{{ title }}</h3>
      </div>
      <button
        class="btn btn-secondary btn-compact"
        :disabled="!hasAnyContent"
        @click="$emit('next-batch')"
      >
        换一批
      </button>
    </div>
    <section class="grid-2 related-grid mt-16">
      <!-- Left card -->
      <div class="card">
        <p class="eyebrow">{{ leftLabel }}</p>
        <div v-if="loading" class="muted">正在整理相关推荐...</div>
        <div v-else-if="!leftItems.length" class="muted">{{ leftEmptyMessage }}</div>
        <div v-else class="form-grid">
          <RouterLink
            v-for="item in leftItems"
            :key="item.id"
            :to="isPostVariant ? `/community/${item.id}` : `/explore/${item.id}`"
            class="card related-link-card"
          >
            <template v-if="isPostVariant">
              <strong>{{ item.title }}</strong>
              <p class="muted">{{ item.author_name }} · {{ item.destination_name || "未关联景点" }}</p>
            </template>
            <template v-else>
              <strong>{{ item.name }}</strong>
              <p class="muted">{{ item.city }} · {{ item.province }}</p>
            </template>
          </RouterLink>
        </div>
      </div>

      <!-- Right card -->
      <div class="card">
        <p class="eyebrow">{{ rightLabel }}</p>
        <div v-if="loading" class="muted">正在整理相关推荐...</div>
        <div v-else-if="!rightItems.length" class="muted">{{ rightEmptyMessage }}</div>
        <div v-else class="form-grid">
          <RouterLink
            v-for="item in rightItems"
            :key="item.id"
            :to="isPostVariant ? `/explore/${item.id}` : `/community/${item.id}`"
            class="card related-link-card"
          >
            <template v-if="isPostVariant">
              <strong>{{ item.name }}</strong>
              <p class="muted">{{ item.city }} · {{ item.province }}</p>
            </template>
            <template v-else>
              <strong>{{ item.title }}</strong>
              <p class="muted">{{ item.author_name }} · {{ item.destination_name || "未关联景点" }}</p>
            </template>
          </RouterLink>
        </div>
      </div>
    </section>
  </article>
</template>
