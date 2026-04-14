import { onBeforeUnmount, onMounted, ref } from "vue";

export const useReadingProgress = () => {
  const progress = ref(0);

  const updateProgress = () => {
    if (typeof window === "undefined") return;
    const doc = document.documentElement;
    const scrollTop = window.scrollY || doc.scrollTop || 0;
    const scrollable = Math.max(doc.scrollHeight - window.innerHeight, 0);
    progress.value = scrollable > 0 ? Math.min(100, Math.round((scrollTop / scrollable) * 100)) : 0;
  };

  onMounted(() => {
    updateProgress();
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
  });

  onBeforeUnmount(() => {
    window.removeEventListener("scroll", updateProgress);
    window.removeEventListener("resize", updateProgress);
  });

  return { readingProgress: progress, updateReadingProgress: updateProgress };
};
