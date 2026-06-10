class OmniauthCallbacksController < ApplicationController
  skip_before_action :verify_authenticity_token
  skip_before_action :check_if_login_required

  def azure_oauth2
    auth = request.env['omniauth.auth']
    return redirect_to signin_path, alert: 'Autenticação inválida.' unless auth

    email = auth.info.email&.downcase
    return redirect_to signin_path, alert: 'Email não retornado pelo Azure AD.' unless email

    user = User.find_by_mail(email)

    if user.nil?
      user = User.new(
        login:     email.split('@').first.gsub(/[^a-z0-9_\-@\.]/, '_'),
        firstname: auth.info.first_name || auth.info.name&.split(' ')&.first || 'Usuário',
        lastname:  auth.info.last_name  || auth.info.name&.split(' ')&.last  || 'Azure',
        mail:      email,
        status:    User::STATUS_ACTIVE
      )
      user.random_password
      unless user.save
        return redirect_to signin_path, alert: "Erro ao criar usuário: #{user.errors.full_messages.join(', ')}"
      end
    end

    return redirect_to signin_path, alert: 'Conta inativa. Contate o administrador.' unless user.active?

    self.logged_user = user
    redirect_to home_url
  end

  def failure
    redirect_to signin_path, alert: "Autenticação falhou: #{params[:message]&.humanize}"
  end
end
