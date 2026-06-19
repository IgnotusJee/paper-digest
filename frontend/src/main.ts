import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'vfonts/Lato.css'
import 'vfonts/FiraCode.css'

import App from './App.vue'
import router from './router'

const app = App
const pinia = createPinia()

createApp(app).use(pinia).use(router).mount('#app')
