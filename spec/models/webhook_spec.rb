# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Webhook, type: :model do
  describe 'associations' do
    it { is_expected.to belong_to(:user) }
    it { is_expected.to have_and_belong_to_many(:projects) }
  end

  describe 'validations' do
    it { is_expected.to validate_presence_of(:url) }
    it { is_expected.to validate_length_of(:url).is_at_most(2000) }
    it { is_expected.to validate_length_of(:secret).is_at_most(255) }
  end

  describe 'scopes' do
    describe '.active' do
      it 'returns only active webhooks' do
        active_webhook = create(:webhook, active: true)
        inactive_webhook = create(:webhook, active: false)

        expect(Webhook.active).to include(active_webhook)
        expect(Webhook.active).not_to include(inactive_webhook)
      end
    end
  end

  describe '.trigger' do
    let(:user) { create(:user) }
    let(:project) { create(:project) }
    let(:issue) { create(:issue, project: project) }

    it 'triggers active webhooks for the event' do
      webhook = create(:webhook, user: user, active: true, events: ['issue.created'])
      webhook.projects << project

      allow(user).to receive(:allowed_to?).and_return(true)
      allow(issue).to receive(:visible?).and_return(true)

      expect(WebhookJob).to receive(:perform_later)

      Webhook.trigger('issue.created', issue)
    end
  end

  describe '#payload' do
    let(:user) { create(:user) }
    let(:webhook) { create(:webhook, user: user) }
    let(:issue) { create(:issue) }

    it 'generates a payload hash' do
      payload = webhook.payload('issue.created', issue)

      expect(payload).to be_a(Hash)
      expect(payload).to have_key(:event)
    end
  end

  describe '#call' do
    let(:webhook) { create(:webhook, url: 'https://example.com/webhook') }
    let(:payload_json) { '{"event":"test"}' }

    context 'when request succeeds' do
      it 'returns true' do
        stub_request(:post, webhook.url).to_return(status: 200)

        expect(webhook.call(payload_json)).to be true
      end
    end

    context 'when request fails' do
      it 'returns false and logs error' do
        stub_request(:post, webhook.url).to_raise(StandardError.new('Connection error'))

        expect(Rails.logger).to receive(:warn)
        expect(webhook.call(payload_json)).to be false
      end
    end
  end

  describe 'Executor' do
    describe '#compute_signature' do
      it 'computes HMAC-SHA256 signature' do
        executor = Webhook::Executor.new('https://example.com', '{"test":1}', 'secret123')
        signature = executor.compute_signature

        expect(signature).to start_with('sha256=')
        expect(signature.length).to be > 10
      end
    end
  end
end
