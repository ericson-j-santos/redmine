import { createApp } from 'vue'
import App from './App.vue'
import { createPinia } from 'pinia'
import router from './router'
import axios from 'axios'

import 'vuetify/styles'
import { createVuetify } from 'vuetify'

const app = createApp(App)
const pinia = createPinia()
const vuetify = createVuetify()

axios.defaults.baseURL = 'http://localhost:8000/api'

axios.interceptors.request.use(config => {
  if (!config.headers) config.headers = {}
  if (!('x-correlation-id' in config.headers)) {
    config.headers['x-correlation-id'] = crypto.randomUUID()
  }
  if (!('X-User-Role' in config.headers)) {
    config.headers['X-User-Role'] = 'analista'
  }
  return config
})

app.use(pinia)
app.use(router)
app.use(vuetify)

app.mount('#app')
