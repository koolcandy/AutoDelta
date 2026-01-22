"""
项目安装配置文件
"""
from setuptools import setup, find_packages

setup(
    name='autodelta',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'opencv-python',
        'numpy',
        'scrcpy',
    ],
    author='AutoDelta Team',
    description='Automated game bot for Delta Force Mobile',
    python_requires='>=3.7',
)