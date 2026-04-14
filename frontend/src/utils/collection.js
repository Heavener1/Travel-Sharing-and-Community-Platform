export const getFavoriteIds = (storageKey) => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const saveFavoriteIds = (storageKey, ids) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey, JSON.stringify(ids));
};

export const toggleFavoriteId = (storageKey, id) => {
  const current = new Set(getFavoriteIds(storageKey));
  if (current.has(id)) {
    current.delete(id);
  } else {
    current.add(id);
  }
  const next = Array.from(current);
  saveFavoriteIds(storageKey, next);
  return next;
};

export const hasFavoriteId = (storageKey, id) => getFavoriteIds(storageKey).includes(id);

export const shareContent = async ({ title, path, summary, onSuccess, onError }) => {
  if (typeof window === "undefined") return false;
  const absoluteUrl = new URL(path, window.location.origin).toString();
  try {
    if (navigator.share) {
      await navigator.share({
        title,
        text: summary || title,
        url: absoluteUrl,
      });
    } else if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(absoluteUrl);
    } else {
      const input = document.createElement("input");
      input.value = absoluteUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
    }
    onSuccess?.();
    return true;
  } catch (error) {
    if (error?.name === "AbortError") {
      return false;
    }
    onError?.(error);
    return false;
  }
};
