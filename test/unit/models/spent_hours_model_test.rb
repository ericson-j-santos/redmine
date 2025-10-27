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

class SpentHoursModelTest < ActiveSupport::TestCase
  fixtures :issues, :time_entries, :users, :trackers, :issue_statuses, :projects, :roles, :members, :member_roles, :activities

  def setup
    @issue = Issue.find(1)
    @user = User.find(2)  # jsmith user from fixtures
    User.current = @user
  end

  def teardown
    User.current = nil
  end

  def test_issue_spent_hours_with_no_time_entries
    TimeEntry.delete_all
    @issue.reload

    assert_equal 0, @issue.spent_hours
  end

  def test_issue_spent_hours_with_single_time_entry
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 5.0,
      spent_on: Date.today,
      activity_id: 9
    )

    @issue.reload
    assert_equal 5.0, @issue.spent_hours
  end

  def test_issue_spent_hours_with_multiple_time_entries
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 2.5,
      spent_on: Date.today,
      activity_id: 9
    )
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 3.0,
      spent_on: Date.today - 1.day,
      activity_id: 9
    )
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 1.5,
      spent_on: Date.today - 2.days,
      activity_id: 9
    )

    @issue.reload
    assert_equal 7.0, @issue.spent_hours
  end

  def test_issue_spent_hours_with_fractional_values
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 1.5,
      spent_on: Date.today,
      activity_id: 9
    )
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 2.75,
      spent_on: Date.today,
      activity_id: 9
    )

    @issue.reload
    assert_equal 4.25, @issue.spent_hours
  end

  def test_total_spent_hours_without_children
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user: @user,
      hours: 5.0,
      spent_on: Date.today,
      activity_id: 9
    )

    @issue.reload
    assert_equal 5.0, @issue.total_spent_hours
  end

  def test_total_spent_hours_includes_child_issues
    parent = Issue.find(1)
    TimeEntry.delete_all

    # Create child issue
    child = Issue.create!(
      project_id: parent.project_id,
      subject: 'Child Issue',
      tracker_id: 1,
      parent_issue_id: parent.id,
      author_id: @user.id
    )

    # Add time to parent
    TimeEntry.create!(
      issue_id: parent.id,
      user_id: @user.id,
      hours: 3.0,
      spent_on: Date.today,
      activity_id: 9
    )

    # Add time to child
    TimeEntry.create!(
      issue_id: child.id,
      user_id: @user.id,
      hours: 2.0,
      spent_on: Date.today,
      activity_id: 9
    )

    parent.reload
    assert_equal 3.0, parent.spent_hours
    assert_equal 5.0, parent.total_spent_hours
  end

  def test_total_spent_hours_with_multiple_levels
    # Create hierarchy: parent -> child -> grandchild
    parent = Issue.find(1)
    TimeEntry.delete_all

    child = Issue.create!(
      project_id: parent.project_id,
      subject: 'Child',
      tracker_id: 1,
      parent_issue_id: parent.id,
      author_id: @user.id
    )

    grandchild = Issue.create!(
      project_id: parent.project_id,
      subject: 'Grandchild',
      tracker_id: 1,
      parent_issue_id: child.id,
      author_id: @user.id
    )

    TimeEntry.create!(
      issue_id: parent.id,
      user_id: @user.id,
      hours: 1.0,
      spent_on: Date.today,
      activity_id: 9
    )
    TimeEntry.create!(
      issue_id: child.id,
      user_id: @user.id,
      hours: 2.0,
      spent_on: Date.today,
      activity_id: 9
    )
    TimeEntry.create!(
      issue_id: grandchild.id,
      user_id: @user.id,
      hours: 3.0,
      spent_on: Date.today,
      activity_id: 9
    )

    parent.reload
    # Parent total should include all descendants
    assert_equal 6.0, parent.total_spent_hours
  end

  def test_spent_hours_ordering_scope
    TimeEntry.delete_all

    # Create issues with different spent hours
    issue1 = Issue.create!(
      project_id: @issue.project_id,
      subject: 'Issue 1',
      tracker_id: 1,
      author_id: @user.id
    )
    issue2 = Issue.create!(
      project_id: @issue.project_id,
      subject: 'Issue 2',
      tracker_id: 1,
      author_id: @user.id
    )
    issue3 = Issue.create!(
      project_id: @issue.project_id,
      subject: 'Issue 3',
      tracker_id: 1,
      author_id: @user.id
    )

    TimeEntry.create!(issue_id: issue1.id, user_id: @user.id, hours: 2.0, spent_on: Date.today, activity_id: 9)
    TimeEntry.create!(issue_id: issue2.id, user_id: @user.id, hours: 5.0, spent_on: Date.today, activity_id: 9)
    TimeEntry.create!(issue_id: issue3.id, user_id: @user.id, hours: 3.0, spent_on: Date.today, activity_id: 9)

    # Order by spent_hours descending
    ordered = [issue1, issue2, issue3].sort_by { |i| -i.spent_hours }
    assert_equal [issue2, issue3, issue1], ordered
  end

  def test_spent_hours_visibility_per_project
    # Create issue in project with time_tracking enabled
    project1 = Project.find(1)
    project1.enable_module!(:time_tracking)

    issue1 = Issue.create!(
      project_id: project1.id,
      subject: 'Issue P1',
      tracker_id: 1,
      author_id: @user.id
    )

    # Create issue in project with time_tracking disabled
    project3 = Project.find(3)
    project3.disable_module!(:time_tracking)

    issue3 = Issue.create!(
      project_id: project3.id,
      subject: 'Issue P3',
      tracker_id: 1,
      author_id: @user.id
    )

    TimeEntry.delete_all
    TimeEntry.create!(issue_id: issue1.id, user_id: @user.id, hours: 5.0, spent_on: Date.today, activity_id: 9)
    TimeEntry.create!(issue_id: issue3.id, user_id: @user.id, hours: 3.0, spent_on: Date.today, activity_id: 9)

    issue1.reload
    issue3.reload

    # Both should calculate spent_hours
    assert_equal 5.0, issue1.spent_hours
    assert_equal 3.0, issue3.spent_hours
  end

  def test_spent_hours_with_deleted_time_entries
    issue = Issue.create!(
      project_id: @issue.project_id,
      subject: 'Test Issue',
      tracker_id: 1,
      author_id: @user.id
    )

    TimeEntry.delete_all
    entry1 = TimeEntry.create!(
      issue_id: issue.id,
      user_id: @user.id,
      hours: 5.0,
      spent_on: Date.today,
      activity_id: 9
    )
    TimeEntry.create!(
      issue_id: issue.id,
      user_id: @user.id,
      hours: 3.0,
      spent_on: Date.today,
      activity_id: 9
    )

    issue.reload
    assert_equal 8.0, issue.spent_hours

    # Delete one entry
    entry1.destroy
    issue.reload
    assert_equal 3.0, issue.spent_hours
  end

  def test_spent_hours_calculation_accuracy
    issue = Issue.create!(
      project_id: @issue.project_id,
      subject: 'Accuracy Test',
      tracker_id: 1,
      author_id: @user.id
    )

    TimeEntry.delete_all
    # Test with various decimal values
    [0.25, 0.5, 0.75, 1.25, 1.5, 1.75].each_with_index do |hours, i|
      TimeEntry.create!(
        issue_id: issue.id,
        user_id: @user.id,
        hours: hours,
        spent_on: Date.today - i.days,
        activity_id: 9
      )
    end

    issue.reload
    expected = 0.25 + 0.5 + 0.75 + 1.25 + 1.5 + 1.75
    assert_equal expected, issue.spent_hours
  end

  def test_spent_hours_with_zero_values
    TimeEntry.delete_all
    TimeEntry.create!(
      issue_id: @issue.id,
      user_id: @user.id,
      hours: 0.0,
      spent_on: Date.today,
      activity_id: 9
    )

    @issue.reload
    assert_equal 0.0, @issue.spent_hours
  end

  def test_spent_hours_scope_ordering_descending
    TimeEntry.delete_all

    issues = 3.times.map do |i|
      issue = Issue.create!(
        project_id: @issue.project_id,
        subject: "Issue #{i}",
        tracker_id: 1,
        author_id: @user.id
      )
      TimeEntry.create!(
        issue_id: issue.id,
        user_id: @user.id,
        hours: (i + 1).to_f,
        spent_on: Date.today,
        activity_id: 9
      )
      issue.reload
      issue
    end

    # Sort by spent_hours descending
    sorted = issues.sort_by { |i| -i.spent_hours }
    assert_equal [3.0, 2.0, 1.0], sorted.map(&:spent_hours)
  end

  def test_spent_hours_scope_ordering_ascending
    TimeEntry.delete_all

    issues = 3.times.map do |i|
      issue = Issue.create!(
        project_id: @issue.project_id,
        subject: "Issue #{i}",
        tracker_id: 1,
        author_id: @user.id
      )
      TimeEntry.create!(
        issue_id: issue.id,
        user_id: @user.id,
        hours: (i + 1).to_f,
        spent_on: Date.today,
        activity_id: 9
      )
      issue.reload
      issue
    end

    # Sort by spent_hours ascending
    sorted = issues.sort_by(&:spent_hours)
    assert_equal [1.0, 2.0, 3.0], sorted.map(&:spent_hours)
  end

  def test_total_spent_hours_scope_ordering
    TimeEntry.delete_all

    parent = Issue.find(1)

    child1 = Issue.create!(
      project_id: parent.project_id,
      subject: 'Child 1',
      tracker_id: 1,
      parent_issue_id: parent.id,
      author_id: @user.id
    )
    child2 = Issue.create!(
      project_id: parent.project_id,
      subject: 'Child 2',
      tracker_id: 1,
      parent_issue_id: parent.id,
      author_id: @user.id
    )

    TimeEntry.create!(issue_id: parent.id, user_id: @user.id, hours: 1.0, spent_on: Date.today, activity_id: 9)
    TimeEntry.create!(issue_id: child1.id, user_id: @user.id, hours: 2.0, spent_on: Date.today, activity_id: 9)
    TimeEntry.create!(issue_id: child2.id, user_id: @user.id, hours: 3.0, spent_on: Date.today, activity_id: 9)

    parent.reload

    # Parent's total should be 1 + 2 + 3 = 6
    assert_equal 6.0, parent.total_spent_hours
  end
end
