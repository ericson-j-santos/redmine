# frozen_string_literal: true

require 'rails_helper'

RSpec.describe MailHandler do
  let(:project) { create(:project, identifier: 'test-project') }
  let(:user) { create(:user, mail: 'user@example.com') }

  describe '.receive' do
    let(:email_content) do
      <<~EMAIL
        From: #{user.mail}
        To: redmine@example.com
        Subject: New issue from email
        
        This is the issue description from email.
      EMAIL
    end

    context 'with valid email' do
      it 'creates an issue from email' do
        allow(Project).to receive(:find_by).and_return(project)
        allow(User).to receive(:find_by_mail).and_return(user)

        expect do
          MailHandler.receive(email_content, project: 'test-project')
        end.to change(Issue, :count).by(1)
      end
    end

    context 'with unknown sender' do
      it 'does not create an issue' do
        allow(User).to receive(:find_by_mail).and_return(nil)

        expect do
          MailHandler.receive(email_content, project: 'test-project')
        end.not_to change(Issue, :count)
      end
    end

    context 'with reply to existing issue' do
      let(:issue) { create(:issue, project: project, author: user) }
      let(:reply_content) do
        <<~EMAIL
          From: #{user.mail}
          To: redmine@example.com
          Subject: Re: [#{project.identifier} - #{issue.tracker.name} ##{issue.id}] #{issue.subject}
          
          This is a reply to the issue.
        EMAIL
      end

      it 'adds a note to the issue' do
        allow(Project).to receive(:find_by).and_return(project)
        allow(User).to receive(:find_by_mail).and_return(user)

        expect do
          MailHandler.receive(reply_content)
        end.to change { issue.journals.count }.by(1)
      end
    end
  end
end
