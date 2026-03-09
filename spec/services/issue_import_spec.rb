# frozen_string_literal: true

require 'rails_helper'

RSpec.describe IssueImport do
  let(:user) { create(:user) }
  let(:project) { create(:project) }

  describe '#build_object' do
    it 'builds an issue from CSV data' do
      csv_data = {
        'subject' => 'Test Issue',
        'description' => 'Test description',
        'priority' => 'Normal'
      }
      
      import = IssueImport.new
      import.user = user
      import.settings = { 'project_id' => project.id }
      
      issue = import.build_object(csv_data)
      
      expect(issue).to be_a(Issue)
      expect(issue.subject).to eq('Test Issue')
    end
  end

  describe '#save_object' do
    it 'saves the issue' do
      issue = create(:issue, project: project)
      import = IssueImport.new
      
      expect(import.save_object(issue)).to be true
      expect(issue).to be_persisted
    end
  end
end
