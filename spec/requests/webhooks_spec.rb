# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Webhooks API', type: :request do
  let(:user) { create(:user, :admin) }
  let(:webhook) { create(:webhook, user: user) }

  before do
    user.update(api_key: 'test_api_key') if user.respond_to?(:api_key=)
  end

  describe 'GET /webhooks' do
    it 'returns all webhooks for current user' do
      create_list(:webhook, 2, user: user)

      get '/webhooks'

      expect(response).to have_http_status(:success)
    end
  end

  describe 'POST /webhooks' do
    let(:valid_params) do
      {
        webhook: {
          url: 'https://example.com/hook',
          events: ['issue.created', 'issue.updated'],
          active: true
        }
      }
    end

    it 'creates a new webhook' do
      expect do
        post '/webhooks', params: valid_params
      end.to change(Webhook, :count).by(1)

      expect(response).to redirect_to(webhooks_path)
    end

    it 'returns error for invalid URL' do
      post '/webhooks', params: { webhook: { url: 'invalid-url' } }

      expect(response).to have_http_status(:success)
      expect(Webhook.count).to eq(0)
    end
  end

  describe 'PUT /webhooks/:id' do
    it 'updates the webhook' do
      put "/webhooks/#{webhook.id}", params: { webhook: { active: false } }

      webhook.reload
      expect(webhook.active).to be false
    end
  end

  describe 'DELETE /webhooks/:id' do
    it 'deletes the webhook' do
      webhook_to_delete = create(:webhook, user: user)

      expect do
        delete "/webhooks/#{webhook_to_delete.id}"
      end.to change(Webhook, :count).by(-1)

      expect(response).to redirect_to(webhooks_path)
    end
  end
end
