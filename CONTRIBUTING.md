# Contributing to AutomationBot

Thank you for your interest in contributing to AutomationBot! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Git for version control
- Polygon.io API key for market data

### Development Setup
1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/AutomationBot.git
   cd AutomationBot
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy environment template and configure API keys:
   ```bash
   cp .env.template .env
   # Edit .env with your API credentials
   ```

## Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise (under 50 lines when possible)

### Architecture Principles
- **Modular Design**: Keep components loosely coupled
- **Configuration Driven**: Use JSON config files and environment variables
- **Error Handling**: Comprehensive exception handling with proper logging
- **Testing**: Write tests for new features and bug fixes

### Project Structure
```
AutomationBot/
├── api/                      # Web interface and API routes
├── core/                     # Core trading engine and business logic
├── providers/                # External API integrations
├── config/                   # Configuration files
├── simple_modular_main.py    # Application entry point
└── requirements.txt          # Python dependencies
```

## Contributing Process

### 1. Issue Reporting
- Search existing issues before creating new ones
- Provide detailed reproduction steps for bugs
- Include system information (Python version, OS, etc.)
- Use issue templates when available

### 2. Feature Proposals
- Open an issue to discuss new features before implementation
- Describe the use case and expected benefits
- Consider impact on existing functionality
- Get maintainer approval before starting work

### 3. Pull Request Process
1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes following the coding standards
3. Test your changes thoroughly
4. Update documentation if needed
5. Commit with descriptive messages:
   ```bash
   git commit -m "Add feature: brief description of changes"
   ```
6. Push to your fork and create a pull request
7. Respond to code review feedback

### 4. Code Review
- All contributions require code review
- Address reviewer feedback promptly
- Maintain a respectful and constructive tone
- Be open to suggestions and improvements

## Types of Contributions

### Bug Fixes
- Fix crashes, incorrect behavior, or performance issues
- Include test cases to prevent regression
- Document the root cause in commit messages

### New Trading Strategies
- Implement new algorithmic trading strategies
- Follow the existing strategy interface pattern
- Include backtesting results and documentation
- Consider risk management implications

### Infrastructure Improvements
- Performance optimizations
- Better error handling and logging
- Database schema improvements
- API enhancements

### Documentation
- Improve README and setup instructions
- Add code comments and docstrings
- Create tutorials and examples
- Fix typos and clarify explanations

## Testing Guidelines

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_portfolio.py

# Run with coverage
python -m pytest --cov=core
```

### Test Requirements
- Write unit tests for new functions
- Include integration tests for API endpoints
- Test error conditions and edge cases
- Maintain test coverage above 80%

## API and Database Changes

### API Changes
- Maintain backward compatibility when possible
- Document breaking changes in pull request
- Update API documentation in README
- Test all endpoints thoroughly

### Database Schema
- Create migration scripts for schema changes
- Test migrations with sample data
- Document new fields and tables
- Consider performance implications

## Security Considerations

### Sensitive Data
- Never commit API keys, passwords, or tokens
- Use environment variables for all credentials
- Review .gitignore before committing
- Be cautious with logging sensitive information

### Code Security
- Validate all user inputs
- Use parameterized queries for database access
- Follow HTTPS best practices
- Implement proper authentication for production features

## Communication

### Discussion Channels
- GitHub Issues for bug reports and feature requests
- Pull Request comments for code-specific discussions
- Project Wiki for detailed documentation

### Getting Help
- Check existing documentation first
- Search closed issues for solutions
- Ask specific questions with context
- Be patient and respectful when requesting help

## Recognition

Contributors are recognized through:
- GitHub contributor statistics
- Mention in release notes for significant contributions
- Credit in documentation for major features

## License

By contributing to AutomationBot, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

Thank you for contributing to AutomationBot! Your help makes the project better for everyone.