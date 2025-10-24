# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Issue, type: :model do
  describe 'validations' do
    it { is_expected.to validate_presence_of(:subject) }
  end

  describe 'attributes' do
    let(:project) { create(:project) }

    it 'can instantiate with project and subject' do
      issue = Issue.new(project_id: project.id, subject: 'Test Issue')
      expect(issue.subject).to eq('Test Issue')
      expect(issue.project_id).to eq(project.id)
    end

    it 'validates subject presence' do
      issue = Issue.new(project_id: project.id)
      expect(issue.valid?).to be false
    end
  end
end
