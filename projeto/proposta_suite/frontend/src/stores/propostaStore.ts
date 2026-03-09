import { defineStore } from 'pinia'
import axios from 'axios'

export const usePropostaStore = defineStore('proposta', {
  state: () => ({
    carregando: false,
    propostaAtual: null as any | null,
    statusProposta: null as any | null,
    erro: null as string | null
  }),

  actions: {
    async criarProposta(dadosProposta: any) {
      this.carregando = true
      this.erro = null
      try {
        const resp = await axios.post('/propostas', dadosProposta)
        this.propostaAtual = resp.data
        return resp.data
      } catch (e: any) {
        this.erro = 'Falha ao enviar proposta para processamento.'
        console.error('[Proposta] Erro criarProposta', e)
        throw e
      } finally {
        this.carregando = false
      }
    },

    async buscarStatus(idProposta: string) {
      this.carregando = true
      this.erro = null
      try {
        const resp = await axios.get(`/propostas/${idProposta}/status`)
        this.statusProposta = resp.data
        return resp.data
      } catch (e: any) {
        this.erro = 'Falha ao consultar status da proposta.'
        console.error('[Proposta] Erro buscarStatus', e)
        throw e
      } finally {
        this.carregando = false
      }
    }
  }
})
