from setuptools import setup, find_packages

setup(
    name="barg",
    version="0.1.0",
    description="Barni's tiny parser grammar for parsing strings/code",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
