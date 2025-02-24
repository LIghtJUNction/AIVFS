from setuptools import setup, find_packages

setup(
    name="aivfs",
    version="1.0.0",
    author="LightJunction",
    author_email="your.email@example.com",
    description="一个基于元数据的AI虚拟文件系统",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/LightJunction/AIVFS",
    project_urls={
        "Bug Tracker": "https://github.com/LightJunction/AIVFS/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "typing-extensions>=4.0.0",
    ],
)