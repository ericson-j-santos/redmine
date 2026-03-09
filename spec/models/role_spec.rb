# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Role, type: :model do
  describe 'validations' do
    it { is_expected.to validate_presence_of(:name) }
    it { is_expected.to validate_length_of(:name).is_at_most(255) }
  end

  describe 'associations' do
    it { is_expected.to have_many(:member_roles).dependent(:destroy) }
    it { is_expected.to have_many(:members).through(:member_roles) }
    it { is_expected.to have_many(:workflow_rules) }
  end

  describe '#permissions=' do
    it 'sets permissions as an array' do
      role = create(:role)
      role.permissions = ['view_issues', 'add_issues']

      expect(role.permissions).to include('view_issues', 'add_issues')
    end
  end

  describe '#add_permission!' do
    it 'adds a permission to the role' do
      role = create(:role, permissions: ['view_issues'])
      role.add_permission!(:edit_issues)

      expect(role.permissions).to include('view_issues', 'edit_issues')
    end
  end

  describe '#remove_permission!' do
    it 'removes a permission from the role' do
      role = create(:role, permissions: ['view_issues', 'edit_issues'])
      role.remove_permission!(:edit_issues)

      expect(role.permissions).to include('view_issues')
      expect(role.permissions).not_to include('edit_issues')
    end
  end

  describe '#has_permission?' do
    it 'returns true when role has the permission' do
      role = create(:role, permissions: ['view_issues'])

      expect(role.has_permission?(:view_issues)).to be true
    end

    it 'returns false when role does not have the permission' do
      role = create(:role, permissions: ['view_issues'])

      expect(role.has_permission?(:delete_issues)).to be false
    end
  end
end
