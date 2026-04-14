import http from "./http";
import { clearFavoriteIds, getFavoriteEntries, getFavoriteIds, saveFavoriteIds, toggleFavoriteId } from "../utils/collection";

const DESTINATION_KEY = "travel_favorite_destinations";
const POST_KEY = "travel_favorite_posts";

export const syncLocalFavoritesToCloud = async () => {
  const localDestinationEntries = getFavoriteEntries(DESTINATION_KEY);
  const localPostEntries = getFavoriteEntries(POST_KEY);
  if (!localDestinationEntries.length && !localPostEntries.length) {
    return { destinationIds: [], postIds: [] };
  }

  const [serverDestinationIds, serverPostIds] = await Promise.all([
    fetchFavoriteDestinationIds(true),
    fetchFavoritePostIds(true),
  ]);

  const destinationSyncTargets = localDestinationEntries
    .map((item) => item.id)
    .filter((id) => !serverDestinationIds.includes(id));
  const postSyncTargets = localPostEntries
    .map((item) => item.id)
    .filter((id) => !serverPostIds.includes(id));

  await Promise.all([
    ...destinationSyncTargets.map((id) => http.post(`/travel/destinations/${id}/favorite/`)),
    ...postSyncTargets.map((id) => http.post(`/social/posts/${id}/favorite/`)),
  ]);

  clearFavoriteIds(DESTINATION_KEY);
  clearFavoriteIds(POST_KEY);

  const [destinationIds, postIds] = await Promise.all([
    fetchFavoriteDestinationIds(true),
    fetchFavoritePostIds(true),
  ]);
  return { destinationIds, postIds };
};

export const fetchFavoriteDestinations = async (authenticated) => {
  if (!authenticated) {
    return getFavoriteEntries(DESTINATION_KEY);
  }
  const { data } = await http.get("/travel/favorites/destinations/");
  return (data.results || []).map((item) => ({
    id: item.destination.id,
    favorited_at: item.favorited_at,
    destination: item.destination,
  }));
};

export const fetchFavoritePosts = async (authenticated) => {
  if (!authenticated) {
    return getFavoriteEntries(POST_KEY);
  }
  const { data } = await http.get("/social/favorites/posts/");
  return (data.results || []).map((item) => ({
    id: item.post.id,
    favorited_at: item.favorited_at,
    post: item.post,
  }));
};

export const fetchFavoriteDestinationIds = async (authenticated) => {
  const items = await fetchFavoriteDestinations(authenticated);
  return items.map((item) => item.id);
};

export const fetchFavoritePostIds = async (authenticated) => {
  const items = await fetchFavoritePosts(authenticated);
  return items.map((item) => item.id);
};

export const toggleDestinationFavorite = async (id, authenticated) => {
  if (!authenticated) {
    return {
      favorited: toggleFavoriteId(DESTINATION_KEY, id).includes(id),
      ids: getFavoriteIds(DESTINATION_KEY),
    };
  }
  const { data } = await http.post(`/travel/destinations/${id}/favorite/`);
  const ids = await fetchFavoriteDestinationIds(true);
  return { favorited: data.favorited, ids };
};

export const togglePostFavorite = async (id, authenticated) => {
  if (!authenticated) {
    return {
      favorited: toggleFavoriteId(POST_KEY, id).includes(id),
      ids: getFavoriteIds(POST_KEY),
    };
  }
  const { data } = await http.post(`/social/posts/${id}/favorite/`);
  const ids = await fetchFavoritePostIds(true);
  return { favorited: data.favorited, ids };
};

export const clearLocalFavorites = () => {
  clearFavoriteIds(DESTINATION_KEY);
  clearFavoriteIds(POST_KEY);
};

export const removeDestinationFavorites = async (ids, authenticated) => {
  if (!authenticated) {
    const next = getFavoriteIds(DESTINATION_KEY).filter((id) => !ids.includes(id));
    saveFavoriteIds(DESTINATION_KEY, next);
    return next;
  }
  await Promise.all(ids.map((id) => http.post(`/travel/destinations/${id}/favorite/`)));
  return fetchFavoriteDestinationIds(true);
};

export const removePostFavorites = async (ids, authenticated) => {
  if (!authenticated) {
    const next = getFavoriteIds(POST_KEY).filter((id) => !ids.includes(id));
    saveFavoriteIds(POST_KEY, next);
    return next;
  }
  await Promise.all(ids.map((id) => http.post(`/social/posts/${id}/favorite/`)));
  return fetchFavoritePostIds(true);
};
