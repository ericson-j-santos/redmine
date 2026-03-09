# frozen_string_literal: true

require 'rails_helper'

RSpec.describe IssuesHelper, type: :helper do
  describe '#issue_heading' do
    let(:issue) { create(:issue) }

    it 'formats the issue heading' do
      heading = helper.issue_heading(issue)

      expect(heading).to include(issue.tracker.name)
      expect(heading).to include("##{issue.id}")
    end
  end

  describe '#issue_status_badge' do
    let(:status) { create(:issue_status, name: 'Open') }

    it 'creates a status badge' do
      badge = helper.issue_status_badge(status)

      expect(badge).to include('Open')
      expect(badge).to include('badge')
    end
  end

  describe '#issue_fields_rows' do
    let(:issue) { create(:issue) }

    it 'returns field rows for display' do
      rows = helper.issue_fields_rows

      expect(rows).to be_an(Array)
      expect(rows).not_to be_empty
    end
  end
end
