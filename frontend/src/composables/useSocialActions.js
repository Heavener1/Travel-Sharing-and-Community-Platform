import { ref } from "vue";
import {
  fetchFavoriteDestinationIds,
  toggleDestinationFavorite,
  fetchFavoritePostIds,
  togglePostFavorite,
} from "../api/favorites";
import { shareContent } from "../utils/collection";

/**
 * Composable for destination favorites & sharing.
 *
 * @param {object} authStore - reactive auth store (must expose `isAuthenticated`)
 * @param {object} uiStore   - reactive ui store (must expose `pushToast`)
 * @returns {{ favoriteIds, syncFavoriteIds, isFavorite, toggleFavorite, shareItem }}
 */
export function useDestinationFavorites(authStore, uiStore) {
  const favoriteIds = ref([]);

  const syncFavoriteIds = async () => {
    favoriteIds.value = await fetchFavoriteDestinationIds(authStore.isAuthenticated);
  };

  const isFavorite = (id) => favoriteIds.value.includes(id);

  const toggleFavorite = async (item) => {
    const { favorited, ids } = await toggleDestinationFavorite(
      item.id,
      authStore.isAuthenticated,
    );
    favoriteIds.value = ids;
    uiStore.pushToast(
      favorited ? `已收藏 ${item.name}` : `已取消收藏 ${item.name}`,
      "success",
    );
  };

  const shareItem = async (item) => {
    await shareContent({
      title: item.name,
      path: `/explore/${item.id}`,
      summary: item.summary,
      onSuccess: () => uiStore.pushToast("景点链接已准备好", "success"),
      onError: () => uiStore.pushToast("分享失败，请稍后再试"),
    });
  };

  return { favoriteIds, syncFavoriteIds, isFavorite, toggleFavorite, shareItem };
}

/**
 * Composable for post favorites & sharing.
 *
 * @param {object} authStore - reactive auth store (must expose `isAuthenticated`)
 * @param {object} uiStore   - reactive ui store (must expose `pushToast`)
 * @returns {{ favoriteIds, syncFavoriteIds, isFavorite, toggleFavorite, sharePost }}
 */
export function usePostFavorites(authStore, uiStore) {
  const favoriteIds = ref([]);

  const syncFavoriteIds = async () => {
    favoriteIds.value = await fetchFavoritePostIds(authStore.isAuthenticated);
  };

  const isFavorite = (id) => favoriteIds.value.includes(id);

  const toggleFavorite = async (post) => {
    const { favorited, ids } = await togglePostFavorite(
      post.id,
      authStore.isAuthenticated,
    );
    favoriteIds.value = ids;
    uiStore.pushToast(
      favorited ? `已收藏《${post.title}》` : `已取消收藏《${post.title}》`,
      "success",
    );
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

  return { favoriteIds, syncFavoriteIds, isFavorite, toggleFavorite, sharePost };
}
