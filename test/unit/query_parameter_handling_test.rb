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

require_relative '../test_helper'

class QueryParameterHandlingTest < ActiveSupport::TestCase
  fixtures :projects, :users, :roles, :members, :member_roles, :issues, :trackers, :issue_statuses

  def test_column_names_handles_single_string_parameter
    query = IssueQuery.new
    # Test with single string (should not raise NoMethodError)
    assert_nothing_raised do
      query.column_names = 'subject'
    end
    assert_equal [:subject], query.column_names
  end

  def test_column_names_handles_array_parameter
    query = IssueQuery.new
    # Test with array (existing behavior)
    assert_nothing_raised do
      query.column_names = ['subject', 'status']
    end
    assert_equal [:subject, :status], query.column_names
  end

  def test_add_filters_handles_single_string_parameter
    query = IssueQuery.new
    # Test with single string field (should not raise NoMethodError)
    assert_nothing_raised do
      query.add_filters('status_id', {'status_id' => 'o'}, {'status_id' => ['1']})
    end
    assert query.has_filter?('status_id')
  end

  def test_add_filters_handles_array_parameter
    query = IssueQuery.new
    # Test with array of fields (existing behavior)
    assert_nothing_raised do
      query.add_filters(['status_id', 'priority_id'], 
                       {'status_id' => 'o', 'priority_id' => '='}, 
                       {'status_id' => ['1'], 'priority_id' => ['1']})
    end
    assert query.has_filter?('status_id')
    assert query.has_filter?('priority_id')
  end

  def test_build_from_params_with_single_column_parameter
    query = IssueQuery.new
    # Simulates query parameter c=subject (single value, not array)
    params = {c: 'subject'}
    assert_nothing_raised do
      query.build_from_params(params)
    end
  end

  def test_build_from_params_with_single_filter_parameter
    query = IssueQuery.new
    # Simulates query parameter f=status_id&op[status_id]=o (single value)
    params = {f: 'status_id', op: {'status_id' => 'o'}}
    assert_nothing_raised do
      query.build_from_params(params)
    end
  end
end
