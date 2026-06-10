Rails.application.routes.draw do
  match 'auth/azure_oauth2/callback',
        to: 'omniauth_callbacks#azure_oauth2',
        via: [:get, :post],
        as: :omniauth_azure_callback

  match 'auth/failure',
        to: 'omniauth_callbacks#failure',
        via: [:get, :post],
        as: :omniauth_failure
end
