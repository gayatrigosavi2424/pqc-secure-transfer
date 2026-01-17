#!/usr/bin/env python3
"""
Setup script for PQC Secure Transfer System
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pqc-secure-transfer",
    version="1.0.0",
    author="PQC Secure Transfer Contributors",
    author_email="your-email@example.com",
    description="Post-Quantum Cryptography secure data transfer system for federated learning",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pqc-secure-transfer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security :: Cryptography",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "full": ["liboqs-python>=0.8.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pqc-server=examples.server:main",
            "pqc-client=examples.client:main",
            "pqc-demo=simple_demo:main",
        ],
    },
    keywords="post-quantum cryptography, federated learning, secure transfer, encryption, quantum-safe",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/pqc-secure-transfer/issues",
        "Source": "https://github.com/yourusername/pqc-secure-transfer",
        "Documentation": "https://github.com/yourusername/pqc-secure-transfer#readme",
    },
)