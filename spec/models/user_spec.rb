# frozen_string_literal: true

require 'rails_helper'

RSpec.describe User, type: :model do
  describe 'attributes' do
    let(:user) { build(:user) }

    it 'has a login' do
      expect(user.login).to be_present
    end

    it 'has a firstname' do
      expect(user.firstname).to be_present
    end

    it 'has mail' do
      expect(user.mail).to be_present
    end

    it 'can be admin' do
      admin = build(:admin_user)
      expect(admin.admin).to be true
    end

    it 'can be inactive' do
      inactive = build(:user, :inactive)
      expect(inactive.status).to eq(3)
    end
  end

  describe 'validations' do
    it { is_expected.to validate_presence_of(:login) }
  end
end
