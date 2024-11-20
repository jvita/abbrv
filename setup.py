from setuptools import setup, find_packages

# Read the contents of your README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="abbrv",
    version="0.1.0",
    author="Anonymized",
    author_email="your.email@example.com",
    description="A framework for designing and using shorthand fonts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/change-this-once-you-set-up-an-anonymous-profile",
    packages=find_packages(),  # Automatically find packages in the current directory
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "Flask>=3.1.0",
        "numpy>=2.0.2",
        "scipy>=1.13.1",
        "matplotlib>=3.9.2",
    ],
    entry_points={
        # Example of a console script
        "console_scripts": [
            "your-command=your_package.your_module:main_function",
        ],
    },
    include_package_data=True,  # Include non-Python files specified in MANIFEST.in
    package_data={
        # Include package-specific data files
        "your_package": ["data/*.txt"],
    },
    extras_require={
        # Optional dependencies for development or testing
        "dev": ["pytest", "flake8"],
    },
)
