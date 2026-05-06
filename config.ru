# This file is used by Rack-based servers to start the application.

# Render may start Puma with RACK_ENV/RAILS_ENV=deployment, but Redmine only
# defines production/development/test environments. Normalize to production.
if ENV['RACK_ENV'] == 'deployment' || ENV['RAILS_ENV'] == 'deployment'
  ENV['RACK_ENV'] = 'production'
  ENV['RAILS_ENV'] = 'production'
end

require_relative 'config/environment'
run Rails.application
