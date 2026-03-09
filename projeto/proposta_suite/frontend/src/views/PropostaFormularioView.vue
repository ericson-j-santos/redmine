<template>
  <v-container max-width="800">
    <v-card>
      <v-card-title>Cadastro de Proposta</v-card-title>
      <v-card-text>
        <v-alert
          v-if="store.erro"
          type="error"
          class="mb-4"
          variant="tonal"
        >
          {{ store.erro }}
        </v-alert>

        <v-form v-if="!store.carregando" @submit.prevent="onSubmit">
          <v-text-field v-model="form.cpf" label="CPF" required />
          <v-text-field v-model="form.nome_cliente" label="Nome" required />
          <v-text-field v-model="form.email" label="E-mail" required />
          <v-text-field v-model="form.telefone" label="Telefone" />

          <v-text-field
            v-model.number="form.valor_solicitado"
            label="Valor solicitado"
            prefix="R$"
            type="number"
            required
          />
          <v-text-field
            v-model.number="form.prazo_meses"
            label="Prazo (meses)"
            type="number"
            required
          />

          <v-select
            v-model="form.tipo_imovel"
            :items="['RESIDENCIAL', 'COMERCIAL']"
            label="Tipo de imóvel"
            required
          />

          <v-select
            v-model="form.tipo_operacao"
            :items="['PORTABILIDADE', 'NOVO_CREDITO']"
            label="Tipo de operação"
            required
          />

          <v-checkbox
            v-model="form.aceite_lgpd"
            label="Li e aceito os termos de uso e privacidade"
            required
          />

          <v-btn type="submit" color="primary" class="mt-4">
            Simular e enviar por e-mail
          </v-btn>
        </v-form>

        <v-skeleton-loader
          v-else
          type="card, list-item-two-line, actions"
        />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { usePropostaStore } from '@/stores/propostaStore'

const router = useRouter()
const store = usePropostaStore()

const form = reactive({
  cpf: '',
  nome_cliente: '',
  email: '',
  telefone: '',
  valor_solicitado: 0,
  prazo_meses: 360,
  tipo_imovel: 'RESIDENCIAL',
  tipo_operacao: 'PORTABILIDADE',
  canal_origem: 'SITE',
  aceite_lgpd: false
})

async function onSubmit() {
  try {
    const resp = await store.criarProposta(form)
    router.push({
      name: 'proposta-acompanhamento',
      params: { idProposta: resp.id_proposta }
    })
  } catch {
    // erro já tratado na store
  }
}
</script>
