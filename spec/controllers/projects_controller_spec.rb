# frozen_string_literal: true

require 'rails_helper'

RSpec.describe ProjectsController, type: :controller do
  let(:user) { create(:user, :admin) }
  let(:project) { create(:project) }

  before do
    @request.session[:user_id] = user.id
  end

  describe 'GET #index' do
    it 'returns a successful response' do
      get :index
      expect(response).to be_successful
    end

    it 'assigns @projects' do
      project
      get :index
      expect(assigns(:projects)).to be_present
    end
  end

  describe 'GET #show' do
    it 'returns a successful response' do
      get :show, params: { id: project.identifier }
      expect(response).to be_successful
    end

    it 'assigns @project' do
      get :show, params: { id: project.identifier }
      expect(assigns(:project)).to eq(project)
    end
  end

  describe 'GET #new' do
    it 'returns a successful response' do
      get :new
      expect(response).to be_successful
    end

    it 'assigns a new project' do
      get :new
      expect(assigns(:project)).to be_a_new(Project)
    end
  end

  describe 'POST #create' do
    let(:valid_attributes) do
      {
        name: 'New Project',
        identifier: 'new-project',
        is_public: true
      }
    end

    context 'with valid parameters' do
      it 'creates a new project' do
        expect do
          post :create, params: { project: valid_attributes }
        end.to change(Project, :count).by(1)
      end

      it 'redirects to settings' do
        post :create, params: { project: valid_attributes }
        expect(response).to redirect_to(settings_project_path(Project.last))
      end
    end

    context 'with invalid parameters' do
      it 'does not create a new project' do
        expect do
          post :create, params: { project: valid_attributes.merge(name: '') }
        end.not_to change(Project, :count)
      end
    end
  end

  describe 'GET #settings' do
    it 'returns a successful response' do
      get :settings, params: { id: project.identifier }
      expect(response).to be_successful
    end
  end

  describe 'PUT #update' do
    context 'with valid parameters' do
      it 'updates the project' do
        put :update, params: { id: project.identifier, project: { name: 'Updated Name' } }
        project.reload
        expect(project.name).to eq('Updated Name')
      end
    end
  end

  describe 'POST #archive' do
    it 'archives the project' do
      post :archive, params: { id: project.identifier }
      project.reload
      expect(project.status).to eq(Project::STATUS_ARCHIVED)
    end
  end

  describe 'POST #unarchive' do
    it 'unarchives the project' do
      project.update(status: Project::STATUS_ARCHIVED)
      post :unarchive, params: { id: project.identifier }
      project.reload
      expect(project.status).to eq(Project::STATUS_ACTIVE)
    end
  end

  describe 'DELETE #destroy' do
    it 'destroys the project' do
      project_to_delete = create(:project)
      expect do
        delete :destroy, params: { id: project_to_delete.identifier }
      end.to change(Project, :count).by(-1)
    end
  end
end
