# Contributing to PQC Secure Transfer

Thank you for your interest in contributing to the PQC Secure Transfer System! This project aims to provide quantum-resistant secure data transfer for federated learning applications.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of cryptography and federated learning

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/pqc-secure-transfer.git
   cd pqc-secure-transfer
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # Install development dependencies
   ```

4. **Install PQC Library (Optional)**
   ```bash
   pip install liboqs-python  # For full post-quantum cryptography support
   ```

5. **Run Tests**
   ```bash
   python test_system.py
   python simple_demo.py
   ```

## 🛠️ Development Guidelines

### Code Style

- **Python Style**: Follow PEP 8
- **Formatting**: Use `black` for code formatting
- **Linting**: Use `flake8` for linting
- **Type Hints**: Use type hints where appropriate

```bash
# Format code
black pqc_secure_transfer/ examples/ *.py

# Lint code
flake8 pqc_secure_transfer/ examples/ *.py

# Type checking
mypy pqc_secure_transfer/
```

### Testing

- **Unit Tests**: Add tests for new functionality
- **Integration Tests**: Test component interactions
- **Performance Tests**: Benchmark critical paths
- **Security Tests**: Validate cryptographic implementations

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_streaming_encryptor.py

# Run with coverage
python -m pytest --cov=pqc_secure_transfer tests/
```

### Documentation

- **Docstrings**: Use Google-style docstrings
- **README**: Update README.md for new features
- **Examples**: Add examples for new functionality
- **Comments**: Comment complex cryptographic operations

## 🔒 Security Considerations

### Cryptographic Code

- **No Custom Crypto**: Use established libraries (liboqs, cryptography)
- **Constant Time**: Ensure timing-safe operations
- **Key Management**: Follow secure key handling practices
- **Testing**: Thoroughly test cryptographic functions

### Code Review

- **Security Review**: All crypto-related changes need security review
- **Performance Impact**: Consider performance implications
- **Backward Compatibility**: Maintain API compatibility when possible

## 📝 Contribution Process

### 1. Issue First

- **Bug Reports**: Use the bug report template
- **Feature Requests**: Use the feature request template
- **Security Issues**: Email security@example.com (private disclosure)

### 2. Branch Strategy

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Create bugfix branch
git checkout -b bugfix/issue-number-description
```

### 3. Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(crypto): add ML-DSA signature support
fix(streaming): handle large file edge cases
docs(readme): update installation instructions
test(key_manager): add key rotation tests
```

### 4. Pull Request

1. **Create PR**: Use the PR template
2. **Tests Pass**: Ensure all tests pass
3. **Documentation**: Update relevant documentation
4. **Review**: Address review feedback
5. **Merge**: Maintainer will merge when ready

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions/methods
   - Mock external dependencies
   - Fast execution (<1s per test)

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Use real dependencies where possible
   - Moderate execution time (<10s per test)

3. **Performance Tests** (`tests/performance/`)
   - Benchmark critical operations
   - Test with large datasets
   - Generate performance reports

4. **Security Tests** (`tests/security/`)
   - Test cryptographic correctness
   - Validate against known attack vectors
   - Test edge cases and error conditions

### Writing Tests

```python
import pytest
from pqc_secure_transfer import StreamingEncryptor

class TestStreamingEncryptor:
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption/decryption preserves data"""
        key = os.urandom(32)
        encryptor = StreamingEncryptor(key)
        
        original_data = b"test data"
        # ... test implementation
        
        assert decrypted_data == original_data
    
    @pytest.mark.performance
    def test_large_file_performance(self):
        """Test performance with large files"""
        # ... performance test implementation
```

## 📚 Areas for Contribution

### High Priority

- **Algorithm Support**: Add support for new NIST PQC algorithms
- **Performance**: Optimize streaming encryption for specific hardware
- **Documentation**: Improve API documentation and examples
- **Testing**: Expand test coverage, especially edge cases

### Medium Priority

- **Monitoring**: Add metrics and monitoring capabilities
- **Deployment**: Improve Docker/Kubernetes configurations
- **Integration**: Add support for more FL frameworks
- **CLI Tools**: Enhance command-line interface

### Low Priority

- **UI/Dashboard**: Web interface for monitoring transfers
- **Plugins**: Plugin system for custom algorithms
- **Benchmarking**: Comprehensive benchmarking suite
- **Examples**: More real-world usage examples

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment**: OS, Python version, dependency versions
- **Steps to Reproduce**: Minimal example that reproduces the issue
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Logs**: Relevant error messages or logs
- **Impact**: How severe is the issue

## 💡 Feature Requests

When requesting features, please include:

- **Use Case**: Why is this feature needed
- **Proposed Solution**: How should it work
- **Alternatives**: Other solutions you've considered
- **Implementation**: Any implementation ideas
- **Breaking Changes**: Will this break existing code

## 🔐 Security Policy

### Reporting Security Issues

- **Private Disclosure**: Email security@example.com
- **No Public Issues**: Don't create public GitHub issues for security bugs
- **Response Time**: We aim to respond within 48 hours
- **Disclosure**: Coordinated disclosure after fix is available

### Security Best Practices

- **Dependencies**: Keep dependencies updated
- **Secrets**: Never commit secrets or keys
- **Crypto**: Use established cryptographic libraries
- **Review**: All crypto code needs security review

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

## 🤝 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Please be respectful and inclusive in all interactions.

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Email**: For security issues and private matters
- **Documentation**: Check README.md and code comments

## 🎉 Recognition

Contributors will be recognized in:

- **CONTRIBUTORS.md**: List of all contributors
- **Release Notes**: Major contributions mentioned in releases
- **README.md**: Special thanks section

Thank you for contributing to making federated learning more secure with post-quantum cryptography!