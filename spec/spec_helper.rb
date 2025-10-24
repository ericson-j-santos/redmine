# frozen_string_literal: true

# SimpleCov configuration - must be first!
if ENV['COVERAGE']
  require 'simplecov'
  SimpleCov.start 'rails' do
    add_filter '/spec/'
    add_filter '/vendor/'
    # Don't enforce minimum coverage - this is a starting point
  end
end

# This file is copied to spec/ when you run 'rails generate rspec:install'
RSpec.configure do |config|
  # Use color in output
  config.color = true

  # Run specs in random order to detect hidden dependencies
  config.order = 'random'

  # Filter out Shoulda matchers warnings
  config.expect_with :rspec do |expectations|
    expectations.include_chain_clauses_in_custom_matcher_descriptions = true
  end

  config.mock_with :rspec do |mocks|
    # This option should be set when all dependencies have been gemified
    # to ensure any upgrades to RSpec are picked up and used
    mocks.verify_partial_doubles = true
  end

  # If you're not using ActiveRecord, or you'd prefer not to run each of your
  # examples within a transaction, comment the following line or assign false
  # instead of true.
  config.use_transactional_fixtures = true

  # RSpec Rails can automatically mix in different behaviours to your tests
  # based on their file location, for example enabling you to call `get` and
  # `post` in specs under `spec/controllers`, `spec/requests` and
  # `spec/integration` respectively.
  config.infer_spec_type_from_file_location!

  # Filter lines from Rails gems in backtraces
  config.filter_gems_from_backtrace "bundler", "bin"
end
