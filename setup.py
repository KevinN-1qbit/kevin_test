from pip._internal.network.session import PipSession
from pip._internal.req import parse_requirements
from setuptools import setup

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements("requirements.txt", session=PipSession())

# convert to list
required = [str(ir.requirement) for ir in install_reqs]

setup(
    name="hansascheduler",
    # version='0.0.0',
    # author='',
    # author_email='',
    # packages='scheduler utils'.split(),
    # license='',
    # description='',
    long_description=open("README.md").read(),
    install_requires=required,
)
