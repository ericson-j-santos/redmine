# frozen_string_literal: true

ENV['RAILS_ENV'] ||= 'test'
require File.expand_path('../config/environment', __dir__)

# Prevent database truncation if the environment is production
abort("The Rails environment is running in production mode!") if Rails.env.production?

require 'rspec/rails'
require 'capybara/rails'
require 'factory_bot_rails'
require 'shoulda/matchers'
require 'rails-controller-testing'

# Checks for pending migrations and applies them before tests are run
begin
  ActiveRecord::Migration.maintain_test_schema!
rescue ActiveRecord::PendingMigrationError => e
  puts e.to_s.strip
  exit 1
end

RSpec.configure do |config|
  # Use Factory Bot for fixtures
  config.include FactoryBot::Syntax::Methods

  # Include helpers for controller tests
  config.include ActionController::TestCase::Behavior, file_path: /spec\/controllers/

  # Use transactional fixtures
  config.use_transactional_fixtures = true

  # Configure Capybara
  config.include Capybara::DSL

  # Infer spec type from file location
  config.infer_spec_type_from_file_location!

  # Filter gems from backtrace
  config.filter_gems_from_backtrace "bundler", "bin"

  # Shoulda Matchers configuration
  Shoulda::Matchers.configure do |matchers|
    matchers.integrate do |with|
      with.test_framework :rspec
      with.library :rails
    end
  end
end
