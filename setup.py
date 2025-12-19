from setuptools import setup, find_packages

setup(
    name="hx_quant",
    version="0.1.0",
    description="慧醒量化交易平台",
    author="Gauss Cheng",
    author_email="GuoXing.Cheng@hxcul.cn",
    packages=find_packages(),
    install_requires=[
        "vnpy",
        "mootdx",
        "vnpy_tdx"
    ],
    entry_points={
    },
)