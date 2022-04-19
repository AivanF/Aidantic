import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="Aidantic",
    version="1.0.1",
    author="AivanF.",
    author_email="projects@aivanf.com",
    description=(
        "Data parsing and validation with OneOf"
        " using Python type hints"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AivanF/Aidantic",
    packages=["aidantic"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Text Processing",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: Freely Distributable",
    ],
)
