# frozen_string_literal: true

require 'rails_helper'

RSpec.describe 'Projects API', type: :request do
  let(:user) { create(:user, :admin) }
  let(:project) { create(:project) }

  before do
    # Autenticação via API key ou session
    user.update(api_key: 'test_api_key')
  end

  describe 'GET /projects' do
    it 'returns all projects' do
      create_list(:project, 3)
      
      get '/projects.json', headers: { 'X-Redmine-API-Key' => user.api_key }
      
      expect(response).to have_http_status(:success)
      json = JSON.parse(response.body)
      expect(json['projects'].count).to be >= 3
    end
  end  describe 'GET /projects/:id' do
    it 'returns a specific project' do
      get "/projects/#{project.identifier}.json"

      expect(response).to have_http_status(:success)
      json = JSON.parse(response.body)
      expect(json['project']['name']).to eq(project.name)
    end

    it 'returns 404 for non-existent project' do
      get '/projects/non-existent.json'

      expect(response).to have_http_status(:not_found)
    end
  end

  describe 'POST /projects' do
    let(:valid_params) do
      {
        project: {
          name: 'API Project',
          identifier: 'api-project',
          is_public: true
        }
      }
    end

    it 'creates a new project' do
      expect do
        post '/projects.json', params: valid_params
      end.to change(Project, :count).by(1)

      expect(response).to have_http_status(:created)
    end

    it 'returns error for invalid data' do
      post '/projects.json', params: { project: { name: '' } }

      expect(response).to have_http_status(:unprocessable_entity)
    end
  end

  describe 'PUT /projects/:id' do
    it 'updates the project' do
      put "/projects/#{project.identifier}.json", params: { project: { name: 'Updated Name' } }

      expect(response).to have_http_status(:no_content)
      project.reload
      expect(project.name).to eq('Updated Name')
    end
  end

  describe 'DELETE /projects/:id' do
    it 'deletes the project' do
      project_to_delete = create(:project)

      expect do
        delete "/projects/#{project_to_delete.identifier}.json"
      end.to change(Project, :count).by(-1)

      expect(response).to have_http_status(:no_content)
    end
  end
end
