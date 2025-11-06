"""
Setup configuration for deutsch_verfahrn package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="deutsch_verfahrn",
    version="0.1.0",
    author="nikitaskostas",
    description="A Tracker of Public Transportation Lateness for Users in Germany",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nikitaskostas/deutsch_verfahrn",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "deutsch-verfahrn=deutsch_verfahrn.cli:main",
        ],
    },
)
