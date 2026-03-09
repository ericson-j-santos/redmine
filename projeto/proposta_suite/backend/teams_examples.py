#!/usr/bin/env python3
"""
Exemplos de uso do Teams Webhook Service na Proposta Suite
"""

import asyncio
import sys
import os

# Adicionar path do app ao sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.teams_webhook_service import (
    teams_service,
    AlertLevel,
    send_custom_message
)


async def exemplo_proposta_criada():
    """Exemplo: Notificação de nova proposta criada"""
    print("📋 Enviando notificação de proposta criada...")
    
    success = await teams_service.send_proposta_criada_alert(
        proposta_id=1234,
        cliente_nome="Empresa ABC Ltda",
        valor=150000.00,
        usuario="Maria Silva"
    )
    
    if success:
        print("✅ Notificação enviada com sucesso!")
    else:
        print("❌ Falha ao enviar notificação")
    
    return success


async def exemplo_proposta_aprovada():
    """Exemplo: Notificação de proposta aprovada"""
    print("\n✅ Enviando notificação de proposta aprovada...")
    
    success = await teams_service.send_proposta_aprovada_alert(
        proposta_id=1234,
        cliente_nome="Empresa ABC Ltda",
        valor=150000.00,
        aprovador="João Santos"
    )
    
    if success:
        print("✅ Notificação enviada com sucesso!")
    else:
        print("❌ Falha ao enviar notificação")
    
    return success


async def exemplo_proposta_rejeitada():
    """Exemplo: Notificação de proposta rejeitada"""
    print("\n❌ Enviando notificação de proposta rejeitada...")
    
    success = await teams_service.send_proposta_rejeitada_alert(
        proposta_id=1235,
        cliente_nome="Empresa XYZ S.A.",
        motivo="Valor fora do orçamento disponível",
        usuario="Carlos Oliveira"
    )
    
    if success:
        print("✅ Notificação enviada com sucesso!")
    else:
        print("❌ Falha ao enviar notificação")
    
    return success


async def exemplo_simulacao():
    """Exemplo: Notificação de simulação concluída"""
    print("\n🔬 Enviando notificação de simulação...")
    
    success = await teams_service.send_simulacao_alert(
        proposta_id=1234,
        cenarios_gerados=5,
        melhor_taxa=2.35
    )
    
    if success:
        print("✅ Notificação enviada com sucesso!")
    else:
        print("❌ Falha ao enviar notificação")
    
    return success


async def exemplo_mensagem_customizada():
    """Exemplo: Notificação customizada"""
    print("\n💬 Enviando mensagem customizada...")
    
    success = await send_custom_message(
        title="🎉 Deploy em Produção",
        message="A aplicação Proposta Suite foi deployada com sucesso!",
        level=AlertLevel.SUCCESS,
        facts=[
            {"title": "Versão", "value": "2.5.0"},
            {"title": "Ambiente", "value": "Produção"},
            {"title": "Tempo de Deploy", "value": "3m 25s"},
            {"title": "Status", "value": "✅ Todos os testes passaram"}
        ]
    )
    
    if success:
        print("✅ Notificação enviada com sucesso!")
    else:
        print("❌ Falha ao enviar notificação")
    
    return success


async def exemplo_erro():
    """Exemplo: Notificação de erro"""
    print("\n🚨 Enviando alerta de erro...")
    
    success = await teams_service.send_error_alert(
        error_type="DatabaseConnectionError",
        error_message="Timeout ao conectar com o banco de dados",
        context={
            "Database": "proposta_suite_prod",
            "Host": "db.exemplo.com:5432",
            "Tentativas": "3",
            "Última Tentativa": "23:45:12"
        }
    )
    
    if success:
        print("✅ Alerta enviado com sucesso!")
    else:
        print("❌ Falha ao enviar alerta")
    
    return success


async def exemplo_notificacao_generica():
    """Exemplo: Notificação genérica com diferentes níveis"""
    print("\n📢 Enviando notificações com diferentes níveis...")
    
    # INFO
    await teams_service.send_notification(
        title="ℹ️ Informação",
        message="Backup agendado será executado em 1 hora.",
        level=AlertLevel.INFO
    )
    print("  ✅ INFO enviado")
    
    await asyncio.sleep(1)
    
    # WARNING
    await teams_service.send_notification(
        title="⚠️ Atenção",
        message="Uso de memória atingiu 75% do limite.",
        level=AlertLevel.WARNING,
        facts=[
            {"title": "Memória Usada", "value": "6 GB"},
            {"title": "Memória Total", "value": "8 GB"},
            {"title": "Percentual", "value": "75%"}
        ]
    )
    print("  ✅ WARNING enviado")
    
    await asyncio.sleep(1)
    
    # SUCCESS
    await teams_service.send_notification(
        title="✅ Sucesso",
        message="Backup concluído com sucesso!",
        level=AlertLevel.SUCCESS,
        facts=[
            {"title": "Tamanho", "value": "2.3 GB"},
            {"title": "Duração", "value": "12 minutos"}
        ]
    )
    print("  ✅ SUCCESS enviado")
    
    return True


async def main():
    """Executa todos os exemplos"""
    print("╔════════════════════════════════════════════════════╗")
    print("║  📢 Exemplos Teams Webhook - Proposta Suite       ║")
    print("╚════════════════════════════════════════════════════╝\n")
    
    # Verificar se está habilitado
    if not teams_service.enabled:
        print("⚠️  Teams Notifications está DESABILITADO")
        print("   Configure TEAMS_NOTIFICATIONS_ENABLED=true")
        print()
    
    if not teams_service.webhook_url:
        print("❌ TEAMS_WEBHOOK_URL não está configurada!")
        print("   Configure a variável de ambiente antes de executar.")
        return
    
    print(f"📍 Webhook URL: {teams_service.webhook_url[:50]}...")
    print(f"🔔 Notifications Enabled: {teams_service.enabled}")
    print(f"⏱️  Timeout: {teams_service.timeout}s")
    print()
    
    # Escolher exemplos para executar
    print("Selecione os exemplos para executar:")
    print("  1. Proposta Criada")
    print("  2. Proposta Aprovada")
    print("  3. Proposta Rejeitada")
    print("  4. Simulação Concluída")
    print("  5. Mensagem Customizada")
    print("  6. Alerta de Erro")
    print("  7. Notificações com Diferentes Níveis")
    print("  8. TODOS os exemplos")
    print()
    
    escolha = input("Digite o número (ou Enter para executar TODOS): ").strip()
    
    if not escolha or escolha == "8":
        # Executar todos
        await exemplo_proposta_criada()
        await asyncio.sleep(2)
        
        await exemplo_proposta_aprovada()
        await asyncio.sleep(2)
        
        await exemplo_proposta_rejeitada()
        await asyncio.sleep(2)
        
        await exemplo_simulacao()
        await asyncio.sleep(2)
        
        await exemplo_mensagem_customizada()
        await asyncio.sleep(2)
        
        await exemplo_erro()
        await asyncio.sleep(2)
        
        await exemplo_notificacao_generica()
    else:
        # Executar exemplo específico
        exemplos = {
            "1": exemplo_proposta_criada,
            "2": exemplo_proposta_aprovada,
            "3": exemplo_proposta_rejeitada,
            "4": exemplo_simulacao,
            "5": exemplo_mensagem_customizada,
            "6": exemplo_erro,
            "7": exemplo_notificacao_generica
        }
        
        func = exemplos.get(escolha)
        if func:
            await func()
        else:
            print("❌ Opção inválida!")
            return
    
    print("\n" + "="*56)
    print("✅ Exemplos concluídos!")
    print("📖 Verifique o canal do Teams para ver as notificações")
    print("="*56)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Execução interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
