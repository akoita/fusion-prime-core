#!/usr/bin/env python3
"""
Fusion Prime - Cross-chain Treasury and Settlement Platform
"""

import os

from setuptools import find_packages, setup


# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()


# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


setup(
    name="fusion-prime",
    version="0.1.0",
    author="Fusion Prime Team",
    author_email="team@fusionprime.dev",
    description="Cross-chain treasury and settlement platform for institutional DeFi",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/akoita/fusion-prime",
    project_urls={
        "Bug Reports": "https://github.com/akoita/fusion-prime/issues",
        "Source": "https://github.com/akoita/fusion-prime",
        "Documentation": "https://github.com/akoita/fusion-prime/blob/main/README.md",
    },
    packages=find_packages(where=".", exclude=["tests*", "scripts*", "contracts*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "bandit>=1.7.0",
            "safety>=2.3.0",
        ],
        "test": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "pytest-xdist>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocs-mermaid2-plugin>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fusion-prime=app.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml", "*.md", "*.txt"],
    },
    zip_safe=False,
    keywords="defi, treasury, settlement, cross-chain, ethereum, smart-contracts",
    license="MIT",
)
