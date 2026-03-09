# frozen_string_literal: true

require 'rails_helper'

RSpec.describe WebhooksController, type: :controller do
  let(:user) { create(:user, :admin) }
  let(:webhook) { create(:webhook, user: user) }

  before do
    @request.session[:user_id] = user.id
  end

  describe 'GET #index' do
    it 'returns a successful response' do
      get :index
      expect(response).to be_successful
    end

    it 'assigns @webhooks' do
      webhook
      get :index
      expect(assigns(:webhooks)).to be_present
    end
  end

  describe 'GET #new' do
    it 'returns a successful response' do
      get :new
      expect(response).to be_successful
    end

    it 'assigns a new webhook' do
      get :new
      expect(assigns(:webhook)).to be_a_new(Webhook)
    end
  end

  describe 'POST #create' do
    let(:valid_attributes) do
      {
        url: 'https://example.com/webhook',
        events: ['issue.created'],
        active: true
      }
    end

    context 'with valid parameters' do
      it 'creates a new webhook' do
        expect do
          post :create, params: { webhook: valid_attributes }
        end.to change(Webhook, :count).by(1)
      end

      it 'redirects to webhooks list' do
        post :create, params: { webhook: valid_attributes }
        expect(response).to redirect_to(webhooks_path)
      end
    end

    context 'with invalid parameters' do
      it 'does not create a new webhook' do
        expect do
          post :create, params: { webhook: valid_attributes.merge(url: '') }
        end.not_to change(Webhook, :count)
      end

      it 'renders new template' do
        post :create, params: { webhook: valid_attributes.merge(url: '') }
        expect(response).to render_template(:new)
      end
    end
  end

  describe 'GET #edit' do
    it 'returns a successful response' do
      get :edit, params: { id: webhook.id }
      expect(response).to be_successful
    end

    it 'assigns @webhook' do
      get :edit, params: { id: webhook.id }
      expect(assigns(:webhook)).to eq(webhook)
    end
  end

  describe 'PUT #update' do
    context 'with valid parameters' do
      it 'updates the webhook' do
        put :update, params: { id: webhook.id, webhook: { url: 'https://new.example.com/hook' } }
        webhook.reload
        expect(webhook.url).to eq('https://new.example.com/hook')
      end

      it 'redirects to webhooks list' do
        put :update, params: { id: webhook.id, webhook: { url: 'https://new.example.com' } }
        expect(response).to redirect_to(webhooks_path)
      end
    end

    context 'with invalid parameters' do
      it 'renders edit template' do
        put :update, params: { id: webhook.id, webhook: { url: '' } }
        expect(response).to render_template(:edit)
      end
    end
  end

  describe 'DELETE #destroy' do
    it 'destroys the webhook' do
      webhook_to_delete = create(:webhook, user: user)
      expect do
        delete :destroy, params: { id: webhook_to_delete.id }
      end.to change(Webhook, :count).by(-1)
    end

    it 'redirects to webhooks list' do
      delete :destroy, params: { id: webhook.id }
      expect(response).to redirect_to(webhooks_path)
    end
  end
end
