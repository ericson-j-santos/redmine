# frozen_string_literal: true

FactoryBot.define do
  factory :user do
    login { Faker::Internet.username }
    firstname { Faker::Name.first_name }
    lastname { Faker::Name.last_name }
    mail { Faker::Internet.email }
    password { 'SecurePassword123!' }
    password_confirmation { 'SecurePassword123!' }
    admin { false }
    status { 1 } # Active

    trait :admin do
      admin { true }
    end

    trait :inactive do
      status { 3 }
    end

    factory :admin_user, traits: [:admin]
  end

  factory :project do
    sequence(:name) { |n| "Project #{n}" }
    sequence(:identifier) { |n| "project-#{n}" }
    description { Faker::Lorem.paragraph }
    is_public { false }
    created_on { Time.current }
    updated_on { Time.current }

    trait :public do
      is_public { true }
    end
  end

  factory :issue do
    project
    subject { Faker::Lorem.sentence }
    description { Faker::Lorem.paragraph }
    
    after(:build) do |issue|
      # Find or create tracker
      issue.tracker ||= Tracker.first || create(:tracker)
      # Find or create status
      issue.status ||= IssueStatus.first || create(:issue_status)
      # Find or create priority - should use enumeration type
      issue.priority_id ||= 3 # Normal priority
    end
    
    created_on { Time.current }
    updated_on { Time.current }

    trait :with_custom_fields do
      transient do
        custom_field_count { 1 }
      end

      after(:create) do |issue, evaluator|
        create_list(:custom_value, evaluator.custom_field_count, customized: issue)
      end
    end
  end

  factory :tracker do
    sequence(:name) { |n| "Tracker #{n}" }
    
    after(:build) do |tracker|
      tracker.default_status_id ||= IssueStatus.first&.id || create(:issue_status).id
    end
  end

  factory :issue_status do
    sequence(:name) { |n| "Status #{n}" }
    is_closed { false }

    trait :closed do
      is_closed { true }
    end
  end

  factory :role do
    name { Faker::Lorem.word }
    permissions { %w[view_issues add_issues edit_issues] }

    trait :admin_role do
      permissions { [] } # Admin has all permissions
    end
  end

  factory :member do
    user
    project
    association :role

    after(:create) do |member|
      member.member_roles.update_all(role_id: member.role.id)
    end
  end

  factory :wiki do
    project
    start_page { 'Wiki' }
  end

  factory :wiki_page do
    wiki
    title { Faker::Lorem.word }

    after(:create) do |wiki_page|
      create(:wiki_content, wiki_page: wiki_page)
    end
  end

  factory :wiki_content do
    wiki_page
    author { association :user }
    text { Faker::Lorem.paragraph }
    comments { 'Initial version' }
  end

  factory :news do
    project
    author { association :user }
    title { Faker::Lorem.sentence }
    description { Faker::Lorem.paragraph }
    created_on { Time.current }
  end

  factory :time_entry do
    user
    project
    issue
    activity_id { 1 } # Development
    hours { 2.5 }
    spent_on { Date.current }
    comments { Faker::Lorem.sentence }
    created_on { Time.current }
    updated_on { Time.current }
  end
end
