from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if not line.startswith("#")]

setup(
    name="barkus",
    version="0.1.0",
    author="Commonwealth",
    author_email="info@example.com",
    description="PDF Barcode Splitter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/barkus",
    py_modules=["barkus"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "barkus=barkus:main",
        ],
    },
)