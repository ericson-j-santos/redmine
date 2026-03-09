# frozen_string_literal: true

require 'rails_helper'

RSpec.describe WebhookJob, type: :job do
  let(:user) { create(:user) }
  let(:webhook) { create(:webhook, user: user, url: 'https://example.com/webhook', secret: 'test_secret') }
  let(:payload) { '{"event":"issue.created","issue":{"id":1}}' }

  describe '#perform' do
    context 'when webhook exists' do
      it 'calls the webhook' do
        stub_request(:post, webhook.url).to_return(status: 200)

        expect do
          WebhookJob.perform_now(webhook.id, payload)
        end.not_to raise_error

        expect(WebMock).to have_requested(:post, webhook.url)
          .with(body: payload)
          .once
      end

      it 'includes HMAC signature in headers' do
        stub_request(:post, webhook.url).to_return(status: 200)

        WebhookJob.perform_now(webhook.id, payload)

        expect(WebMock).to have_requested(:post, webhook.url)
          .with(headers: { 'X-Redmine-Signature-256' => /sha256=.+/ })
      end
    end

    context 'when webhook does not exist' do
      it 'handles missing webhook gracefully' do
        expect do
          WebhookJob.perform_now(99999, payload)
        end.not_to raise_error
      end
    end

    context 'when request fails' do
      it 'logs the error' do
        stub_request(:post, webhook.url).to_raise(StandardError.new('Connection error'))

        expect(Rails.logger).to receive(:warn).with(/Webhook Error/)

        WebhookJob.perform_now(webhook.id, payload)
      end
    end
  end
end
