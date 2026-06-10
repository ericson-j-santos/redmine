require 'omniauth'
require 'omniauth-azure-activedirectory-v2'
require 'omniauth/rails_csrf_protection'

Rails.application.config.middleware.use OmniAuth::Builder do
  provider :azure_activedirectory_v2,
    ENV.fetch('AZURE_CLIENT_ID', ''),
    ENV.fetch('AZURE_CLIENT_SECRET', ''),
    { tenant_id: ENV.fetch('AZURE_TENANT_ID', 'common') }
end

OmniAuth.config.allowed_request_methods = [:get, :post]
OmniAuth.config.silence_get_warning = true
