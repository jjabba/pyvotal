import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyvotal5",
    version="0.0.2",
    author="Karl Berggren",
    author_email="kalle@jjabba.com",
    description="lib for easy access to pivotal tracker's APIv5",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jjabba/pyvotal",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)