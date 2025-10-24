# How to Fork and Clone This Repository

This guide explains how to fork (copy) this Redmine repository to your personal GitHub account and clone it to your local machine.

## Step 1: Fork the Repository on GitHub

1. Go to the repository on GitHub: https://github.com/ericson-j-santos/redmine
2. Click the **"Fork"** button in the upper right corner of the page
3. Select your personal account as the destination for the fork
4. Wait while GitHub creates a copy of the repository in your account

After forking, you'll have your own copy of the repository at `https://github.com/YOUR-USERNAME/redmine`

## Step 2: Clone the Repository to Your Local Machine

After forking, you can clone the repository to your local machine:

```bash
# Clone your fork (replace YOUR-USERNAME with your GitHub username)
git clone https://github.com/YOUR-USERNAME/redmine.git

# Navigate to the repository directory
cd redmine
```

## Step 3: Configure Upstream Remote (Optional)

To keep your fork updated with the original repository, configure the upstream remote:

```bash
# Add the original repository as upstream remote
git remote add upstream https://github.com/ericson-j-santos/redmine.git

# Verify the configured remotes
git remote -v
```

You should see something like:
```
origin    https://github.com/YOUR-USERNAME/redmine.git (fetch)
origin    https://github.com/YOUR-USERNAME/redmine.git (push)
upstream  https://github.com/ericson-j-santos/redmine.git (fetch)
upstream  https://github.com/ericson-j-santos/redmine.git (push)
```

## Step 4: Sync with the Original Repository (Optional)

To update your fork with the latest changes from the original repository:

```bash
# Fetch updates from upstream
git fetch upstream

# Make sure you're on the main branch
git checkout main

# Merge changes from upstream
git merge upstream/main

# Push updates to your fork on GitHub
git push origin main
```

## Working with Your Fork

Now you can work with your fork normally:

```bash
# Create a new branch for your changes
git checkout -b my-feature

# Make your changes and commits
git add .
git commit -m "Description of changes"

# Push to your fork on GitHub
git push origin my-feature
```

## Installation and Configuration

After cloning the repository, follow the installation instructions:

1. Refer to the `doc/INSTALL` file for detailed installation instructions
2. Configure the database as described in the documentation
3. Install dependencies with `bundle install`
4. Run database migrations

## Additional Resources

- Official Redmine documentation: https://www.redmine.org/
- Installation guide: doc/INSTALL
- Upgrade guide: doc/UPGRADING
- Testing guide: doc/RUNNING_TESTS

## Important Note

This is a fork of the official Redmine project. If you want to contribute to the main Redmine project, please visit https://www.redmine.org/ and follow the official contribution guidelines. For this specific fork, please contact the repository maintainer.
