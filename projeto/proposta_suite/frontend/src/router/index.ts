import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import PropostaFormularioView from '@/views/PropostaFormularioView.vue'
import PropostaAcompanhamentoView from '@/views/PropostaAcompanhamentoView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'proposta-form',
    component: PropostaFormularioView
  },
  {
    path: '/propostas/:idProposta',
    name: 'proposta-acompanhamento',
    component: PropostaAcompanhamentoView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
