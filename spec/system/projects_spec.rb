# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Projects Management', type: :system do
  let(:admin) { create(:user, :admin) }

  before do
    driven_by(:rack_test)
    login_as(admin)
  end

  describe 'Creating a project' do
    it 'creates a new project successfully' do
      visit projects_path
      click_link 'New project'

      fill_in 'Name', with: 'New System Test Project'
      fill_in 'Identifier', with: 'new-system-project'
      fill_in 'Description', with: 'This is a test project'

      click_button 'Create'

      expect(page).to have_content('New System Test Project')
    end
  end

  describe 'Viewing projects list' do
    before do
      create_list(:project, 5)
    end

    it 'displays all projects' do
      visit projects_path

      expect(page).to have_css('.project', minimum: 5)
    end
  end

  describe 'Editing a project' do
    let(:project) { create(:project) }

    it 'updates the project' do
      visit settings_project_path(project)

      fill_in 'Name', with: 'Updated Project Name'
      click_button 'Save'

      expect(page).to have_content('Updated Project Name')
    end
  end

  describe 'Archiving a project' do
    let(:project) { create(:project) }

    it 'archives the project' do
      visit settings_project_path(project)
      click_link 'Archive'

      expect(page).to have_content('archived')
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
