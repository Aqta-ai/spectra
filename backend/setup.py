"""
Setup configuration for Spectra backend
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="spectra-backend",
    version="2.0.0",
    author="Anya Chueayen",
    author_email="anya@aqta.ai",
    description="AI screen reader and voice assistant backend",
    long_description="Real-time AI agent that understands your screen and responds to your voice. Built for accessibility, designed for everyone.",
    long_description_content_type="text/plain",
    url="https://github.com/anyaparanya/spectra",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "spectra=app.main:main",
        ],
    },
)