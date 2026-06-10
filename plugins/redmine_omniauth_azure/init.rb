Redmine::Plugin.register :redmine_omniauth_azure do
  name 'Redmine OmniAuth Azure AD'
  author 'Custom'
  description 'Azure AD SSO authentication for Redmine'
  version '1.0.0'
  requires_redmine version_or_higher: '5.0'
end

require_dependency File.join(File.dirname(__FILE__), 'lib', 'redmine_omniauth_azure', 'hooks')
