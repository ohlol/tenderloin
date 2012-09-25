#!/usr/bin/env python

from setuptools import setup, find_packages

version = '0.0.3'

setup(
    name='tenderloin',
    version=version,
    description='Tenderloin is a simple HTTP-based system information server',
    long_description='Tenderloin is a simple HTTP-based system information server',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
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
            'check_tl = tenderloin.cli:checker',
            'tl = tenderloin.cli:server',
            'tc = tenderloin.cli:collector'
        ],
    }
)
