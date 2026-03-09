# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Authentication', type: :request do
  let(:user) { create(:user, password: 'password123', password_confirmation: 'password123') }

  describe 'GET /login' do
    it 'displays the login page' do
      get '/login'

      expect(response).to have_http_status(:success)
      expect(response.body).to include('login')
    end
  end

  describe 'POST /login' do
    context 'with valid credentials' do
      it 'logs in the user' do
        post '/login', params: { username: user.login, password: 'password123' }

        expect(response).to redirect_to(home_path)
      end
    end

    context 'with invalid credentials' do
      it 'shows error message' do
        post '/login', params: { username: user.login, password: 'wrong' }

        expect(response).to have_http_status(:success)
        expect(response.body).to include('Invalid user or password')
      end
    end
  end

  describe 'POST /logout' do
    before do
      allow_any_instance_of(ApplicationController).to receive(:current_user).and_return(user)
    end

    it 'logs out the user' do
      post '/logout'

      expect(response).to redirect_to(home_path)
    end
  end
end
