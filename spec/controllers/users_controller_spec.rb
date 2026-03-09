# frozen_string_literal: true

require 'rails_helper'

RSpec.describe UsersController, type: :controller do
  let(:admin_user) { create(:user, :admin) }
  let(:user) { create(:user) }

  before do
    @request.session[:user_id] = admin_user.id
  end

  describe 'GET #index' do
    it 'returns a successful response' do
      get :index
      expect(response).to be_successful
    end

    it 'assigns @users' do
      user
      get :index
      expect(assigns(:users)).to be_present
    end
  end

  describe 'GET #show' do
    it 'returns a successful response' do
      get :show, params: { id: user.id }
      expect(response).to be_successful
    end

    it 'assigns @user' do
      get :show, params: { id: user.id }
      expect(assigns(:user)).to eq(user)
    end
  end

  describe 'GET #new' do
    it 'returns a successful response' do
      get :new
      expect(response).to be_successful
    end

    it 'assigns a new user' do
      get :new
      expect(assigns(:user)).to be_a_new(User)
    end
  end

  describe 'POST #create' do
    let(:valid_attributes) do
      {
        login: 'newuser',
        firstname: 'New',
        lastname: 'User',
        mail: 'newuser@example.com',
        password: 'SecurePassword123!',
        password_confirmation: 'SecurePassword123!'
      }
    end

    context 'with valid parameters' do
      it 'creates a new user' do
        expect do
          post :create, params: { user: valid_attributes }
        end.to change(User, :count).by(1)
      end

      it 'redirects to edit user path' do
        post :create, params: { user: valid_attributes }
        expect(response).to redirect_to(edit_user_path(User.last))
      end
    end

    context 'with invalid parameters' do
      it 'does not create a new user' do
        expect do
          post :create, params: { user: valid_attributes.merge(login: '') }
        end.not_to change(User, :count)
      end
    end
  end

  describe 'GET #edit' do
    it 'returns a successful response' do
      get :edit, params: { id: user.id }
      expect(response).to be_successful
    end
  end

  describe 'PUT #update' do
    context 'with valid parameters' do
      it 'updates the user' do
        put :update, params: { id: user.id, user: { firstname: 'Updated' } }
        user.reload
        expect(user.firstname).to eq('Updated')
      end

      it 'redirects to edit user path' do
        put :update, params: { id: user.id, user: { firstname: 'Updated' } }
        expect(response).to redirect_to(edit_user_path(user))
      end
    end
  end

  describe 'DELETE #destroy' do
    it 'destroys the user' do
      user_to_delete = create(:user)
      expect do
        delete :destroy, params: { id: user_to_delete.id }
      end.to change(User, :count).by(-1)
    end
  end
end
