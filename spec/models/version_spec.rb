# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Version, type: :model do
  describe 'associations' do
    it { is_expected.to belong_to(:project) }
    it { is_expected.to have_many(:issues).dependent(:nullify) }
  end

  describe 'validations' do
    subject { build(:version) }

    it { is_expected.to validate_presence_of(:name) }
    it { is_expected.to validate_length_of(:name).is_at_most(60) }
    it { is_expected.to validate_length_of(:description).is_at_most(255) }
  end

  describe '#closed?' do
    it 'returns true when status is closed' do
      version = create(:version, status: 'closed')
      expect(version.closed?).to be true
    end

    it 'returns false when status is open' do
      version = create(:version, status: 'open')
      expect(version.closed?).to be false
    end
  end

  describe '#completed_percent' do
    let(:project) { create(:project) }
    let(:version) { create(:version, project: project) }

    it 'returns 0 when there are no issues' do
      expect(version.completed_percent).to eq(0)
    end

    it 'calculates completion based on closed issues' do
      create(:issue, project: project, fixed_version: version, status: create(:issue_status, is_closed: true))
      create(:issue, project: project, fixed_version: version, status: create(:issue_status, is_closed: false))

      expect(version.completed_percent).to be > 0
    end
  end

  describe '#overdue?' do
    it 'returns true when effective_date is in the past and version is not closed' do
      version = create(:version, effective_date: 1.day.ago, status: 'open')
      expect(version.overdue?).to be true
    end

    it 'returns false when effective_date is in the future' do
      version = create(:version, effective_date: 1.day.from_now)
      expect(version.overdue?).to be false
    end

    it 'returns false when version is closed' do
      version = create(:version, effective_date: 1.day.ago, status: 'closed')
      expect(version.overdue?).to be false
    end
  end
end
