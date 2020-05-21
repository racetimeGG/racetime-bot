from setuptools import find_packages, setup


setup(
    name='racetime-bot',
    description='Foundation system for creating chat bots for racetime.gg',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    url='https://github.com/racetimeGG/racetime-bot',
    project_urls={
        'Source': 'https://github.com/racetimeGG/racetime-bot',
    },
    version='1.4.0',
    install_requires=[
        'aiohttp',
        'asgiref',
        'requests',
        'websockets',
    ],
    packages=find_packages(),
)
