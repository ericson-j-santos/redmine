# frozen_string_literal: true

require 'rails_helper'

RSpec.describe IssuesController, type: :controller do
  let(:user) { create(:user) }
  let(:project) { create(:project) }
  let(:issue) { create(:issue, project: project, author: user) }

  before do
    @request.session[:user_id] = user.id
  end

  describe 'GET #index' do
    it 'returns a successful response' do
      get :index
      expect(response).to be_successful
    end

    it 'assigns @issues' do
      issue
      get :index
      expect(assigns(:issues)).to be_present
    end

    it 'filters by project' do
      get :index, params: { project_id: project.identifier }
      expect(response).to be_successful
    end
  end

  describe 'GET #show' do
    it 'returns a successful response' do
      get :show, params: { id: issue.id }
      expect(response).to be_successful
    end

    it 'assigns @issue' do
      get :show, params: { id: issue.id }
      expect(assigns(:issue)).to eq(issue)
    end
  end

  describe 'GET #new' do
    before do
      project.trackers << issue.tracker
    end

    it 'returns a successful response' do
      get :new, params: { project_id: project.identifier }
      expect(response).to be_successful
    end

    it 'assigns a new issue' do
      get :new, params: { project_id: project.identifier }
      expect(assigns(:issue)).to be_a_new(Issue)
    end
  end

  describe 'POST #create' do
    let(:valid_attributes) do
      {
        project_id: project.id,
        tracker_id: issue.tracker.id,
        subject: 'New Issue',
        description: 'Issue description',
        status_id: issue.status.id,
        priority_id: issue.priority_id
      }
    end

    context 'with valid parameters' do
      it 'creates a new issue' do
        expect do
          post :create, params: { issue: valid_attributes }
        end.to change(Issue, :count).by(1)
      end

      it 'redirects to the created issue' do
        post :create, params: { issue: valid_attributes }
        expect(response).to redirect_to(issue_path(Issue.last))
      end
    end

    context 'with invalid parameters' do
      it 'does not create a new issue' do
        expect do
          post :create, params: { issue: valid_attributes.merge(subject: '') }
        end.not_to change(Issue, :count)
      end
    end
  end

  describe 'GET #edit' do
    it 'returns a successful response' do
      get :edit, params: { id: issue.id }
      expect(response).to be_successful
    end
  end

  describe 'PUT #update' do
    context 'with valid parameters' do
      it 'updates the issue' do
        put :update, params: { id: issue.id, issue: { subject: 'Updated Subject' } }
        issue.reload
        expect(issue.subject).to eq('Updated Subject')
      end

      it 'redirects to the issue' do
        put :update, params: { id: issue.id, issue: { subject: 'Updated' } }
        expect(response).to redirect_to(issue_path(issue))
      end
    end
  end

  describe 'DELETE #destroy' do
    it 'destroys the issue' do
      issue_to_delete = create(:issue, project: project, author: user)
      expect do
        delete :destroy, params: { id: issue_to_delete.id }
      end.to change(Issue, :count).by(-1)
    end
  end
end
