# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Issues Management', type: :system do
  let(:user) { create(:user, :admin) }
  let(:project) { create(:project, :public) }
  let(:tracker) { create(:tracker) }
  let(:status) { create(:issue_status) }

  before do
    project.trackers << tracker
    driven_by(:rack_test)
    login_as(user)
  end

  describe 'Creating an issue' do
    it 'creates a new issue successfully' do
      visit project_path(project)
      click_link 'New issue'

      fill_in 'Subject', with: 'Test Issue from System Spec'
      fill_in 'Description', with: 'This is a test issue created via system test'
      select tracker.name, from: 'Tracker'

      click_button 'Create'

      expect(page).to have_content('Issue was successfully created')
      expect(page).to have_content('Test Issue from System Spec')
    end
  end

  describe 'Viewing issues list' do
    before do
      create_list(:issue, 3, project: project)
    end

    it 'displays all issues' do
      visit project_issues_path(project)

      expect(page).to have_css('.issue', count: 3)
    end

    it 'filters issues by status' do
      closed_status = create(:issue_status, :closed)
      create(:issue, project: project, status: closed_status)

      visit project_issues_path(project)
      select 'Closed', from: 'Status'
      click_button 'Apply'

      expect(page).to have_css('.issue', count: 1)
    end
  end

  describe 'Editing an issue' do
    let(:issue) { create(:issue, project: project, subject: 'Original Subject') }

    it 'updates the issue' do
      visit edit_issue_path(issue)

      fill_in 'Subject', with: 'Updated Subject'
      click_button 'Submit'

      expect(page).to have_content('Issue was successfully updated')
      expect(page).to have_content('Updated Subject')
    end
  end

  describe 'Adding a note to an issue' do
    let(:issue) { create(:issue, project: project) }

    it 'adds a note successfully' do
      visit issue_path(issue)

      fill_in 'Notes', with: 'This is a test note'
      click_button 'Submit'

      expect(page).to have_content('This is a test note')
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
