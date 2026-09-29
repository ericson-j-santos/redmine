# frozen_string_literal: true

require "securerandom"

api_key = ENV.fetch("REQSYS_REDMINE_API_KEY")
project_identifier = ENV.fetch("REQSYS_REDMINE_PROJECT_IDENTIFIER", "reqsys-e2e-dev")
login = ENV.fetch("REQSYS_REDMINE_USER_LOGIN", "reqsys_e2e")

unless api_key.match?(/\A[a-f0-9]{40}\z/i)
  abort "REQSYS_REDMINE_API_KEY must be a 40-character hexadecimal token"
end

Setting.rest_api_enabled = "1"

user = User.find_or_initialize_by(login: login)
user.firstname = "ReqSys"
user.lastname = "E2E"
user.mail = "reqsys-e2e@example.invalid"
user.status = Principal::STATUS_ACTIVE
if user.new_record?
  user.password = SecureRandom.base64(36)
  user.password_confirmation = user.password
end
user.save!

token = Token.find_by(user: user, action: "api") || Token.create!(user: user, action: "api")
token.update_column(:value, api_key) unless token.value == api_key

project = Project.find_or_initialize_by(identifier: project_identifier)
project.name = "ReqSys E2E DEV"
project.description = "Projeto isolado para validacao real ReqSys <-> Redmine."
project.is_public = false
project.status = Project::STATUS_ACTIVE
project.save!
project.trackers = Tracker.all if project.trackers.empty?

role = Role.where(builtin: 0).order(:position).first
abort "No regular role available after default data load" unless role

member = Member.find_or_initialize_by(project: project, user: user)
member.roles = [role]
member.save!

puts [
  "REQSYS_REDMINE_BOOTSTRAP_OK",
  "version=#{Redmine::VERSION.to_s}",
  "project_id=#{project.id}",
  "project_identifier=#{project.identifier}",
  "user_id=#{user.id}",
  "api_key_present=true",
  "rest_api_enabled=#{Setting.rest_api_enabled}"
].join(" ")
