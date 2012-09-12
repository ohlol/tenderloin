#!/usr/bin/env python

from setuptools import setup, find_packages

version = '0.0.1'

setup(
    name='tenderloin',
    version=version,
    description='Tenderloin is a simple HTTP-based system information server',
    long_description='Tenderloin is a simple HTTP-based system information server',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD',
        'Topic :: System :: Networking :: Monitoring'
    ],
    keywords='',
    author='Scott Smith',
    author_email='scott@ohlol.net',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['pyzmq', 'requests', 'setuptools', 'tornado'],
    entry_points={
        'console_scripts': [
            'tl = tenderloin.cli:server',
            'tc = tenderloin.cli:collector'
        ],
    }
)
