<script setup>
import { computed } from "vue";
import { marked } from "marked";

const props = defineProps({
  content: {
    type: String,
    default: "",
  },
});

marked.setOptions({
  breaks: true,
  gfm: true,
});

const renderedContent = computed(() => marked.parse(props.content || ""));
</script>

<template>
  <div class="markdown-body" v-html="renderedContent"></div>
</template>
