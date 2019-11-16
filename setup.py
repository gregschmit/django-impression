import os
from setuptools import find_packages, setup
import impression


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# get README
with open("README.rst") as f:
    long_description = f.read()

setup(
    name="django-impression",
    version=impression.__version__,
    packages=find_packages(),
    install_requires=["Django>=2", "djangorestframework>=3", "requests>=2"],
    description="Provide user interface and API for email templates.",
    long_description=long_description,
    url="https://github.com/gregschmit/django-impression",
    author="Gregory N. Schmit",
    author_email="schmitgreg@gmail.com",
    license="MIT",
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
