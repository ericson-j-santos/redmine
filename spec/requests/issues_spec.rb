# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Issues', type: :request do
  let(:project) { create(:project) }
  let(:user) { create(:user) }

  describe 'Project issues' do
    it 'creates issue records' do
      issue_attrs = {
        project_id: project.id,
        subject: 'Test Issue',
        description: 'Test Description'
      }
      
      issue = Issue.new(issue_attrs)
      expect(issue.subject).to eq('Test Issue')
      expect(issue.project_id).to eq(project.id)
    end

    it 'validates issue attributes' do
      issue = Issue.new(description: 'No subject')
      expect(issue.valid?).to be false
    end
  end
end
