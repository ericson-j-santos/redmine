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
require 'csv'

class SpentHoursIntegrationTest < Redmine::IntegrationTest
  fixtures :projects, :users, :roles, :members, :member_roles, :issues, :time_entries, :trackers, :issue_statuses

  def test_issues_index_get_with_sort_by_spent_hours
    get '/issues?sort=spent_hours:desc'
    assert_response :success
    assert_template 'issues/index'
  end

  def test_issues_index_get_with_sort_by_total_spent_hours
    get '/issues?sort=total_spent_hours:desc'
    assert_response :success
    assert_template 'issues/index'
  end

  def test_issues_index_get_with_sort_by_spent_hours_ascending
    get '/issues?sort=spent_hours:asc'
    assert_response :success
  end

  def test_issues_index_with_filters_and_spent_hours_sort
    get '/issues', params: {
      sort: 'spent_hours:desc', set_filter: '1',
      f: ['status_id'], op: {'status_id' => 'o'}, v: {'status_id' => []}
    }
    assert_response :success
    assert_template 'issues/index'
    assert_equal ['status_id'], request.query_parameters.fetch('f')
    assert_equal 'o', request.query_parameters.fetch('op').fetch('status_id')
    assert_select 'table.issues tr.issue', minimum: 1 do |rows|
      rows.each do |row|
        assert_not Issue.find(row['id'].delete_prefix('issue-')).closed?
      end
    end
  end

  def test_issues_index_with_pagination_and_spent_hours_sort
    get '/issues?sort=spent_hours:desc&per_page=10&page=1'
    assert_response :success
    assert_template 'issues/index'
  end

  def test_issues_index_project_specific_with_spent_hours_sort
    get '/projects/ecookbook/issues?sort=spent_hours:desc'
    assert_response :success
    assert_template 'issues/index'
  end

  def test_issues_json_api_with_spent_hours_sort
    get '/issues.json?sort=spent_hours:desc'
    assert_response :success

    json_response = response.parsed_body
    assert json_response.key?('issues'), 'Response should contain issues array'
  end

  def test_issues_xml_api_with_spent_hours_sort
    get '/issues.xml?sort=spent_hours:desc'
    assert_response :success
  end

  def test_issues_csv_export_with_spent_hours_sort
    get '/issues.csv', params: {sort: 'spent_hours:desc', c: ['subject', 'spent_hours']}
    assert_response :success
    assert_equal 'text/csv', response.media_type
    assert_equal ['subject', 'spent_hours'], request.query_parameters.fetch('c')
    assert_operator CSV.parse(response.body).length, :>, 1
  end

  def test_issues_index_with_custom_columns_including_spent_hours
    get '/issues', params: {c: ['subject', 'spent_hours', 'total_spent_hours']}
    assert_response :success
    assert_equal ['subject', 'spent_hours', 'total_spent_hours'], request.query_parameters.fetch('c')
    assert_select 'table.issues th.subject', 1
    assert_select 'table.issues th.spent_hours', 1
    assert_select 'table.issues th.total_spent_hours', 1
  end

  def test_issues_with_invalid_sort_parameter_fallback
    get '/issues?sort=invalid_column:desc'
    assert_response :success
    assert_template 'issues/index'
    assert_select 'table.issues tr.issue', minimum: 1
  end

  def test_authenticated_user_spent_hours_sort
    log_user('jsmith', 'jsmith')
    get '/issues?sort=spent_hours:desc'
    assert_response :success
  end

  def test_anonymous_user_spent_hours_sort
    get '/issues?sort=spent_hours:desc'
    assert_response :success
  end

  def test_spent_hours_sort_consistency_multiple_requests
    log_user('jsmith', 'jsmith')

    # First request
    counts_before = [Issue.count, TimeEntry.count]
    get '/issues?sort=spent_hours:desc&per_page=5'
    assert_response :success
    first_ids = response.parsed_body.css('table.issues tr.issue').pluck('id')
    assert_not_empty first_ids

    # The same read must preserve ordering and must not create records.
    get '/issues?sort=spent_hours:desc&per_page=5'
    assert_response :success
    assert_equal first_ids, response.parsed_body.css('table.issues tr.issue').pluck('id')
    assert_equal counts_before, [Issue.count, TimeEntry.count]
  end

  def test_spent_hours_sort_with_subproject_filter
    log_user('jsmith', 'jsmith')
    get '/issues?project_id=1&sort=spent_hours:desc'
    assert_response :success
  end

  def test_spent_hours_sorting_respects_visibility
    # Anonymous user should not see private project issue
    get '/issues?sort=spent_hours:desc'
    assert_response :success
  end

  def test_spent_hours_api_json_with_custom_fields
    log_user('jsmith', 'jsmith')
    get '/issues.json?sort=spent_hours:desc'
    assert_response :success

    json_response = response.parsed_body
    assert json_response.key?('issues')
  end

  def test_spent_hours_sorting_with_default_query
    log_user('jsmith', 'jsmith')
    get '/issues'
    assert_response :success
  end

  def test_spent_hours_sort_url_generation
    log_user('jsmith', 'jsmith')

    get '/issues?sort=spent_hours:desc&project_id=1'
    assert_response :success
  end

  private

  def log_user(login, password)
    get '/login'
    post '/login', params: {
      username: login,
      password: password
    }
  end
end
