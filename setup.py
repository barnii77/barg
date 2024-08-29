from setuptools import setup, find_packages

setup(
    name="barnii77-barg",
    version="0.1.3",
    description="Barni's tiny parser generator for parsing strings/code",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["regex"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
