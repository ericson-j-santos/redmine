#!/usr/bin/env python3
"""
Script para atribuir uma issue e testar notificações por e-mail
"""

from redminelib import Redmine

REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'
PROJECT_IDENTIFIER = 'proposta-suite'

def main():
    print("="*70)
    print("📧 TESTE DE NOTIFICAÇÃO POR E-MAIL")
    print("="*70)
    
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    
    # Pegar primeira issue "Em andamento"
    issues = list(redmine.project.get(PROJECT_IDENTIFIER).issues)
    issue_teste = None
    
    for issue in issues:
        if issue.status.name == 'Em andamento':
            issue_teste = issue
            break
    
    if not issue_teste:
        # Pegar qualquer issue
        issue_teste = issues[0] if issues else None
    
    if issue_teste:
        print(f"\n📝 Issue selecionada para teste:")
        print(f"   #{issue_teste.id} - {issue_teste.subject}")
        print(f"   Status: {issue_teste.status.name}")
        
        try:
            # Atualizar com comentário para gerar notificação
            redmine.issue.update(
                issue_teste.id,
                notes='🧪 Teste de notificação por e-mail do Redmine.\n\n'
                      'Este comentário foi adicionado automaticamente para testar '
                      'se as notificações por e-mail estão funcionando corretamente.'
            )
            
            print(f"\n✅ Comentário adicionado com sucesso!")
            print(f"\n📬 Verificação de e-mail:")
            print(f"   1. Aguarde alguns minutos")
            print(f"   2. Verifique sua caixa de entrada: ericsonjosedossantos@tieri659.onmicrosoft.com")
            print(f"   3. Verifique também a pasta de SPAM/Lixo Eletrônico")
            print(f"   4. Se não receber, veja o log do Redmine:")
            print(f"      tail -100 log/development.log | grep -i mail")
            
        except Exception as e:
            print(f"\n❌ Erro ao atualizar issue: {e}")
    else:
        print("\n⚠️  Nenhuma issue encontrada no projeto")
    
    print("\n" + "="*70)
    print("💡 CONFIGURAÇÕES IMPORTANTES")
    print("="*70)
    print("""
    Para receber e-mails do Redmine, verifique:
    
    1. Configurações da conta (My Account):
       - Email deve estar preenchido
       - Notificações por email: "Para todos os eventos"
       
    2. Configurações de administração (Admin):
       - Admin > Settings > Email notifications
       - "Emission of emails" deve estar marcado
       
    3. SMTP configurado corretamente:
       - config/configuration.yml
       - Servidor Gmail funcionando
    
    4. Se não receber emails:
       - Verifique logs: log/development.log
       - Teste SMTP diretamente via Rails console
    """)
    
    print()

if __name__ == '__main__':
    main()
