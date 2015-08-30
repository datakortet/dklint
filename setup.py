# -*- coding: utf-8 -*-

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""dklint - postprocessing pylint
"""

classifiers = """\
Development Status :: 3 - Alpha
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Topic :: Software Development :: Libraries
"""

from setuptools import setup, Command

version = '0.1.0'


setup(
    name='dklint',
    version=version,
    license='MIT',
    url='https://github.com/datakortet/dklint',
    install_requires=[
        'pygments',
    ],
    data_files=[
        ('', ['dklint/dklint.rc'])
    ],
    description=__doc__.strip(),
    classifiers=[line for line in classifiers.split('\n') if line],
    long_description=open('README.md').read(),
    # cmdclass={'test': PyTest},
    packages=['dklint'],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'dklint=dklint:main'
        ]
    }
)
