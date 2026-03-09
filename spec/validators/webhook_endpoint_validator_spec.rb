# frozen_string_literal: true

require 'rails_helper'

RSpec.describe WebhookEndpointValidator do
  describe '.safe_webhook_uri?' do
    context 'with valid URLs' do
      it 'accepts https URLs' do
        expect(WebhookEndpointValidator.safe_webhook_uri?('https://example.com/webhook')).to be true
      end

      it 'accepts http URLs for development' do
        allow(Rails.env).to receive(:development?).and_return(true)
        expect(WebhookEndpointValidator.safe_webhook_uri?('http://localhost:3000/webhook')).to be true
      end
    end

    context 'with invalid URLs' do
      it 'rejects file:// URLs' do
        expect(WebhookEndpointValidator.safe_webhook_uri?('file:///etc/passwd')).to be false
      end

      it 'rejects localhost in production' do
        allow(Rails.env).to receive(:production?).and_return(true)
        expect(WebhookEndpointValidator.safe_webhook_uri?('https://localhost/webhook')).to be false
      end

      it 'rejects 127.0.0.1 addresses' do
        expect(WebhookEndpointValidator.safe_webhook_uri?('https://127.0.0.1/webhook')).to be false
      end

      it 'rejects private IP ranges' do
        expect(WebhookEndpointValidator.safe_webhook_uri?('https://192.168.1.1/webhook')).to be false
        expect(WebhookEndpointValidator.safe_webhook_uri?('https://10.0.0.1/webhook')).to be false
      end

      it 'rejects malformed URLs' do
        expect(WebhookEndpointValidator.safe_webhook_uri?('not-a-url')).to be false
      end
    end
  end

  describe 'validation in model' do
    let(:webhook) { build(:webhook, url: url) }

    context 'with valid URL' do
      let(:url) { 'https://example.com/webhook' }

      it 'is valid' do
        expect(webhook).to be_valid
      end
    end

    context 'with invalid URL' do
      let(:url) { 'file:///etc/passwd' }

      it 'is invalid' do
        expect(webhook).not_to be_valid
        expect(webhook.errors[:url]).to be_present
      end
    end
  end
end
