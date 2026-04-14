import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import { pinia } from "./stores";
import { initializeTheme } from "./utils/theme";

initializeTheme();

const app = createApp(App);
app.use(pinia);
app.use(router);
app.mount("#app");
