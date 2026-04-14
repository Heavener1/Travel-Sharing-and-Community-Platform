export const THEMES = [
  { value: "sunset", label: "暖阳" },
  { value: "coast", label: "海岸" },
  { value: "forest", label: "山林" },
];

const STORAGE_KEY = "travel_theme";

export const getStoredTheme = () => {
  const value = localStorage.getItem(STORAGE_KEY);
  return THEMES.some((item) => item.value === value) ? value : "sunset";
};

export const applyTheme = (theme) => {
  const nextTheme = THEMES.some((item) => item.value === theme) ? theme : "sunset";
  document.documentElement.dataset.theme = nextTheme;
  localStorage.setItem(STORAGE_KEY, nextTheme);
  return nextTheme;
};

export const initializeTheme = () => applyTheme(getStoredTheme());
