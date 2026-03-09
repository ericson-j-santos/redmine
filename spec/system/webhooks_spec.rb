# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Webhooks Management', type: :system do
  let(:admin) { create(:user, :admin) }

  before do
    driven_by(:rack_test)
    login_as(admin)
  end

  describe 'Creating a webhook' do
    it 'creates a new webhook successfully' do
      visit webhooks_path
      click_link 'New webhook'

      fill_in 'URL', with: 'https://example.com/webhook'
      check 'issue.created'
      check 'issue.updated'
      check 'Active'

      click_button 'Create'

      expect(page).to have_content('https://example.com/webhook')
    end
  end

  describe 'Viewing webhooks list' do
    before do
      create_list(:webhook, 3, user: admin)
    end

    it 'displays all webhooks' do
      visit webhooks_path

      expect(page).to have_css('.webhook', count: 3)
    end
  end

  describe 'Editing a webhook' do
    let(:webhook) { create(:webhook, user: admin, url: 'https://old.example.com') }

    it 'updates the webhook' do
      visit edit_webhook_path(webhook)

      fill_in 'URL', with: 'https://new.example.com/webhook'
      click_button 'Update'

      expect(page).to have_content('https://new.example.com/webhook')
    end
  end

  describe 'Deleting a webhook' do
    let(:webhook) { create(:webhook, user: admin) }

    it 'deletes the webhook' do
      visit webhooks_path
      click_link 'Delete', href: webhook_path(webhook)

      expect(page).not_to have_content(webhook.url)
    end
  end

  private

  def login_as(user)
    visit signin_path
    fill_in 'Login', with: user.login
    fill_in 'Password', with: 'SecurePassword123!'
    click_button 'Login'
  end
end
