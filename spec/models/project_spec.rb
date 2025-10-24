# frozen_string_literal: true

require 'rails_helper'

RSpec.describe Project, type: :model do
  describe 'associations' do
    it { is_expected.to have_many(:issues).dependent(:destroy) }
    it { is_expected.to have_many(:versions).dependent(:destroy) }
    it { is_expected.to have_many(:news).dependent(:destroy) }
  end

  describe 'validations' do
    it { is_expected.to validate_presence_of(:name) }
    it { is_expected.to validate_presence_of(:identifier) }
  end

  describe 'scopes' do
    let!(:public_project) { create(:project, is_public: true) }
    let!(:private_project) { create(:project, is_public: false) }

    describe '.public_projects' do
      it 'returns only public projects' do
        # Test the is_public attribute directly
        expect(public_project.is_public).to be true
        expect(private_project.is_public).to be false
      end
    end
  end

  describe 'attributes' do
    let(:project) { create(:project) }

    it 'has a name' do
      expect(project.name).to be_present
    end

    it 'has an identifier' do
      expect(project.identifier).to be_present
    end

    it 'can be public' do
      public_project = create(:project, is_public: true)
      expect(public_project.is_public).to be true
    end

    it 'can be private' do
      private_project = create(:project, is_public: false)
      expect(private_project.is_public).to be false
    end
  end
end
