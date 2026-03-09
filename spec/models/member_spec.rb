# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Member, type: :model do
  describe 'associations' do
    it { is_expected.to belong_to(:user) }
    it { is_expected.to belong_to(:project) }
    it { is_expected.to have_many(:member_roles).dependent(:destroy) }
    it { is_expected.to have_many(:roles).through(:member_roles) }
  end

  describe 'validations' do
    subject { build(:member) }

    it { is_expected.to validate_presence_of(:user) }
    it { is_expected.to validate_presence_of(:project) }
  end

  describe 'scopes' do
    describe '.of_project' do
      let(:project1) { create(:project) }
      let(:project2) { create(:project) }

      it 'returns members of specified project' do
        member1 = create(:member, project: project1)
        member2 = create(:member, project: project2)

        expect(Member.where(project: project1)).to include(member1)
        expect(Member.where(project: project1)).not_to include(member2)
      end
    end
  end

  describe '#roles=' do
    it 'assigns roles to the member' do
      member = create(:member)
      role = create(:role)

      member.roles = [role]

      expect(member.roles).to include(role)
    end
  end

  describe '#name' do
    it 'returns the user name' do
      user = create(:user, firstname: 'John', lastname: 'Doe')
      member = create(:member, user: user)

      expect(member.name).to eq(user.name)
    end
  end
end
