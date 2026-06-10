module RedmineOmniauthAzure
  class Hooks < Redmine::Hook::ViewListener
    def view_account_login_form(context = {})
      <<~HTML
        <div style="text-align:center;margin-top:16px;padding-top:16px;border-top:1px solid #ddd;">
          <a href="/auth/azure_oauth2"
             style="display:inline-flex;align-items:center;gap:8px;padding:8px 20px;
                    background:#0078d4;color:#fff;text-decoration:none;
                    border-radius:4px;font-size:14px;font-weight:500;">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 23 23">
              <path fill="#f35325" d="M1 1h10v10H1z"/>
              <path fill="#81bc06" d="M12 1h10v10H12z"/>
              <path fill="#05a6f0" d="M1 12h10v10H1z"/>
              <path fill="#ffba08" d="M12 12h10v10H12z"/>
            </svg>
            Entrar com Microsoft
          </a>
        </div>
      HTML
    end
  end
end
