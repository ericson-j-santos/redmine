# frozen_string_literal: true

require 'rails_helper'

RSpec.describe ApplicationHelper, type: :helper do
  describe '#link_to_project' do
    let(:project) { create(:project, name: 'Test Project') }

    it 'creates a link to the project' do
      link = helper.link_to_project(project)

      expect(link).to include(project.name)
      expect(link).to include(project_path(project))
    end
  end

  describe '#link_to_issue' do
    let(:issue) { create(:issue, subject: 'Test Issue') }

    it 'creates a link to the issue' do
      link = helper.link_to_issue(issue)

      expect(link).to include("##{issue.id}")
      expect(link).to include(issue_path(issue))
    end
  end

  describe '#avatar' do
    let(:user) { create(:user) }

    it 'generates an avatar image' do
      avatar_html = helper.avatar(user)

      expect(avatar_html).to include('gravatar')
    end
  end

  describe '#authoring' do
    let(:user) { create(:user, firstname: 'John', lastname: 'Doe') }
    let(:created_at) { Time.current }

    it 'formats authoring information' do
      authoring = helper.authoring(created_at, user)

      expect(authoring).to include('John Doe')
    end
  end

  describe '#textilizable' do
    it 'converts textile markup to HTML' do
      text = '*bold* text'
      html = helper.textilizable(text)

      expect(html).to include('<strong>')
    end

    it 'handles links' do
      text = '"Example":https://example.com'
      html = helper.textilizable(text)

      expect(html).to include('<a href')
    end
  end
end
