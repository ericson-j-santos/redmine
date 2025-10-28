# frozen_string_literal: true

# Redmine - project management software
# Copyright (C) 2006-  Jean-Philippe Lang
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

require_relative '../../test_helper'

class SpentHoursSimplifiedTest < ActiveSupport::TestCase
  fixtures :issues, :time_entries, :users, :trackers, :issue_statuses, :projects, :roles, :members, :member_roles

  def setup
    @issue = Issue.find(1)
    @user = User.find(2)
    User.current = @user
    # Get or create default activity
    @activity = TimeEntryActivity.first || TimeEntryActivity.create!(name: 'Development')
  end

  def teardown
    User.current = nil
  end

  # Test 1: Issue with no time entries
  def test_issue_spent_hours_with_no_time_entries
    TimeEntry.delete_all
    @issue.reload
    assert_equal 0, @issue.spent_hours
  end

  # Test 2: Issue with single time entry
  def test_issue_spent_hours_with_single_time_entry
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 5.0,
      spent_on: Date.today,
      activity_id: 11
    )
    @issue.reload
    assert_equal 5.0, @issue.spent_hours
  end

  # Test 3: Issue with multiple time entries
  def test_issue_spent_hours_with_multiple_time_entries
    TimeEntry.delete_all
    3.times do |i|
      TimeEntry.create!(
        issue_id: @issue.id,
        user: @user,
        hours: (i + 1).to_f,
        spent_on: Date.today - i.days,
        activity_id: 11
      )
    end
    @issue.reload
    assert_equal 6.0, @issue.spent_hours  # 1 + 2 + 3
  end

  # Test 4: Issue with fractional hours
  def test_issue_spent_hours_with_fractional_values
    TimeEntry.delete_all
    [1.5, 2.75, 0.5].each do |hours|
      TimeEntry.create!(
        issue_id: @issue.id,
        user: @user,
        hours: hours,
        spent_on: Date.today,
        activity_id: 11
      )
    end
    @issue.reload
    assert_equal 4.75, @issue.spent_hours
  end

  # Test 5: Total spent hours calculation
  def test_total_spent_hours_basic
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 8.0,
      spent_on: Date.today,
      activity_id: 11
    )
    @issue.reload
    assert_equal 8.0, @issue.total_spent_hours
  end

  # Test 6: Spent hours with zero values
  def test_spent_hours_with_zero_values
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 0.0,
      spent_on: Date.today,
      activity_id: 11
    )
    @issue.reload
    assert_equal 0.0, @issue.spent_hours
  end

  # Test 7: Spent hours calculation accuracy
  def test_spent_hours_calculation_accuracy
    TimeEntry.delete_all
    decimal_values = [0.25, 0.5, 0.75, 1.25, 1.5, 1.75]
    decimal_values.each_with_index do |hours, i|
      TimeEntry.create!(
        issue_id: @issue.id,
        user: @user,
        hours: hours,
        spent_on: Date.today - i.days,
        activity_id: 11
      )
    end
    @issue.reload
    expected = decimal_values.sum
    assert_equal expected, @issue.spent_hours
  end

  # Test 8: Multiple issues have different spent hours
  def test_different_issues_different_spent_hours
    TimeEntry.delete_all

    issue2 = Issue.find(2)

    # Add time to issue 1
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 5.0,
      spent_on: Date.today,
      activity_id: 11
    )

    # Add time to issue 2
    TimeEntry.create!(
      issue_id: issue2.id,
      user: @user,
      hours: 3.0,
      spent_on: Date.today,
      activity_id: 11
    )

    @issue.reload
    issue2.reload

    assert_equal 5.0, @issue.spent_hours
    assert_equal 3.0, issue2.spent_hours
  end

  # Test 9: Deleting time entry updates spent hours
  def test_spent_hours_after_deletion
    TimeEntry.delete_all

    entry1 = TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 5.0,
      spent_on: Date.today,
      activity_id: 11
    )
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 3.0,
      spent_on: Date.today,
      activity_id: 11
    )

    @issue.reload
    assert_equal 8.0, @issue.spent_hours

    entry1.destroy
    @issue.reload

    assert_equal 3.0, @issue.spent_hours
  end

  def test_spent_hours_accumulates_over_dates
    TimeEntry.delete_all

    today = Date.today
    (1..5).each do |day_offset|
      TimeEntry.create!(
        issue_id: @issue.id,
        user: @user,
        hours: 2.0,
        spent_on: today - day_offset.days,
        activity_id: 11
      )
    end

    @issue.reload
    assert_equal 10.0, @issue.spent_hours
  end
end
