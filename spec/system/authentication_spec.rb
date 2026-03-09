# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'User Authentication', type: :system do
  let(:user) { create(:user, password: 'TestPassword123!', password_confirmation: 'TestPassword123!') }

  before do
    driven_by(:rack_test)
  end

  describe 'Login' do
    it 'logs in with valid credentials' do
      visit signin_path

      fill_in 'Login', with: user.login
      fill_in 'Password', with: 'TestPassword123!'
      click_button 'Login'

      expect(page).to have_content('Logged in')
      expect(page).to have_link('Sign out')
    end

    it 'shows error with invalid credentials' do
      visit signin_path

      fill_in 'Login', with: user.login
      fill_in 'Password', with: 'WrongPassword'
      click_button 'Login'

      expect(page).to have_content('Invalid user or password')
    end
  end

  describe 'Logout' do
    before do
      login_as(user)
    end

    it 'logs out successfully' do
      click_link 'Sign out'

      expect(page).to have_content('Logged out')
    end
  end

  describe 'Registration' do
    before do
      Setting.self_registration = '1'
    end

    it 'registers a new user' do
      visit register_path

      fill_in 'Login', with: 'newuser'
      fill_in 'First name', with: 'New'
      fill_in 'Last name', with: 'User'
      fill_in 'Email', with: 'newuser@example.com'
      fill_in 'Password', with: 'NewPassword123!'
      fill_in 'Confirmation', with: 'NewPassword123!'

      click_button 'Submit'

      expect(page).to have_content('Your account has been activated')
    end
  end

  private

  def login_as(user)
    visit signin_path
    fill_in 'Login', with: user.login
    fill_in 'Password', with: 'TestPassword123!'
    click_button 'Login'
  end
end
