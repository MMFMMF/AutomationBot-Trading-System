#!/bin/bash
# GitHub Repository Setup for AutomationBot-Trading-System
# Run these commands after creating the GitHub repository

echo "Setting up GitHub remote repository..."

# Add GitHub remote (replace YOUR_USERNAME with your actual GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/AutomationBot-Trading-System.git

# Verify remote was added
echo "Remote repositories:"
git remote -v

# Rename branch to main (GitHub standard)
git branch -M main

# Push all commits to GitHub with upstream tracking
echo "Pushing all commits to GitHub..."
git push -u origin main

echo "GitHub repository setup complete!"
echo "Visit: https://github.com/YOUR_USERNAME/AutomationBot-Trading-System"