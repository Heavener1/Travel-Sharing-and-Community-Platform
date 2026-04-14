const normalizeEntry = (value) => {
  if (typeof value === "number" || typeof value === "string") {
    return {
      id: Number(value),
      favorited_at: "",
    };
  }
  if (value && typeof value === "object" && "id" in value) {
    return {
      id: Number(value.id),
      favorited_at: value.favorited_at || "",
    };
  }
  return null;
};

export const getFavoriteEntries = (storageKey) => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.map(normalizeEntry).filter(Boolean);
  } catch {
    return [];
  }
};

export const getFavoriteIds = (storageKey) => getFavoriteEntries(storageKey).map((item) => item.id);

export const saveFavoriteEntries = (storageKey, entries) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey, JSON.stringify(entries));
};

export const saveFavoriteIds = (storageKey, ids) => {
  const entries = ids.map((id) => ({ id, favorited_at: "" }));
  saveFavoriteEntries(storageKey, entries);
};

export const toggleFavoriteId = (storageKey, id) => {
  const current = getFavoriteEntries(storageKey);
  const exists = current.some((item) => item.id === id);
  const next = exists
    ? current.filter((item) => item.id !== id)
    : [{ id, favorited_at: new Date().toISOString() }, ...current];
  saveFavoriteEntries(storageKey, next);
  return next.map((item) => item.id);
};

export const hasFavoriteId = (storageKey, id) => getFavoriteIds(storageKey).includes(id);

export const removeFavoriteIds = (storageKey, idsToRemove) => {
  const removalSet = new Set(idsToRemove);
  const next = getFavoriteEntries(storageKey).filter((item) => !removalSet.has(item.id));
  saveFavoriteEntries(storageKey, next);
  return next.map((item) => item.id);
};

export const clearFavoriteIds = (storageKey) => {
  saveFavoriteEntries(storageKey, []);
  return [];
};

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
