# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Tracker, type: :model do
  describe 'associations' do
    it { is_expected.to belong_to(:default_status).class_name('IssueStatus') }
    it { is_expected.to have_many(:issues) }
    it { is_expected.to have_many(:workflow_rules).dependent(:delete_all) }
    it { is_expected.to have_and_belong_to_many(:projects) }
    it { is_expected.to have_and_belong_to_many(:custom_fields).class_name('IssueCustomField') }
  end

  describe 'validations' do
    subject { create(:tracker) }

    it { is_expected.to validate_presence_of(:name) }
    it { is_expected.to validate_presence_of(:default_status) }
    it { is_expected.to validate_uniqueness_of(:name).case_sensitive }
    it { is_expected.to validate_length_of(:name).is_at_most(30) }
    it { is_expected.to validate_length_of(:description).is_at_most(255) }
  end

  describe 'scopes' do
    describe '.sorted' do
      it 'orders trackers by position' do
        tracker1 = create(:tracker, position: 2)
        tracker2 = create(:tracker, position: 1)

        expect(Tracker.sorted).to eq([tracker2, tracker1])
      end
    end

    describe '.named' do
      it 'finds tracker by name case-insensitive' do
        tracker = create(:tracker, name: 'Bug')

        expect(Tracker.named('bug').first).to eq(tracker)
        expect(Tracker.named('BUG').first).to eq(tracker)
      end
    end
  end

  describe '#to_s' do
    it 'returns the tracker name' do
      tracker = create(:tracker, name: 'Feature')
      expect(tracker.to_s).to eq('Feature')
    end
  end

  describe 'core fields' do
    it 'defines undisablable core fields' do
      expect(Tracker::CORE_FIELDS_UNDISABLABLE).to include('project_id', 'tracker_id', 'subject', 'is_private')
    end

    it 'defines disablable core fields' do
      expect(Tracker::CORE_FIELDS).to include('assigned_to_id', 'category_id', 'start_date', 'due_date')
    end
  end
end
