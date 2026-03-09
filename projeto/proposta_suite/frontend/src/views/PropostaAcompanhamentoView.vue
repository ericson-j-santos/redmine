<template>
  <v-container max-width="800">
    <v-card>
      <v-card-title>Acompanhamento da Proposta</v-card-title>
      <v-card-text>
        <v-alert
          v-if="store.erro"
          type="error"
          class="mb-4"
          variant="tonal"
        >
          {{ store.erro }}
        </v-alert>

        <div v-if="store.carregando">
          <v-skeleton-loader type="card, list-item, actions" />
        </div>

        <div v-else-if="store.statusProposta">
          <p><strong>ID Proposta:</strong> {{ store.statusProposta.id_proposta }}</p>
          <p><strong>Status:</strong> {{ store.statusProposta.status }}</p>

          <div v-if="store.statusProposta.resumo_simulacao" class="mt-4">
            <h3>Resumo da Simulação</h3>
            <p>Valor financiado: R$ {{ store.statusProposta.resumo_simulacao.valor_financiado }}</p>
            <p>Taxa de juros: {{ store.statusProposta.resumo_simulacao.taxa_juros_aa }}% a.a.</p>
            <p>Prazo: {{ store.statusProposta.resumo_simulacao.prazo_meses }} meses</p>
            <p>Parcela aproximada: R$ {{ store.statusProposta.resumo_simulacao.parcela_aproximada }}</p>
          </div>

          <p class="mt-4">
            Última atualização: {{ store.statusProposta.ultimo_update }}
          </p>
        </div>

        <div v-else>
          <p>Nenhuma informação carregada ainda.</p>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { usePropostaStore } from '@/stores/propostaStore'

const route = useRoute()
const store = usePropostaStore()

let intervalId: number | undefined

async function carregarStatus() {
  const idProposta = route.params.idProposta as string
  await store.buscarStatus(idProposta)
}

onMounted(async () => {
  await carregarStatus()
  intervalId = window.setInterval(carregarStatus, 5000)
})

onBeforeUnmount(() => {
  if (intervalId) window.clearInterval(intervalId)
})
</script>
