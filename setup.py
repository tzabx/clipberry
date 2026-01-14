from setuptools import setup, find_packages

setup(
    name="clipberry",
    version="0.1.0",
    description="Cross-platform clipboard sync application",
    author="",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "PySide6>=6.6.0",
        "aiohttp>=3.9.0",
        "websockets>=12.0",
        "zeroconf>=0.131.0",
        "cryptography>=41.0.0",
        "Pillow>=10.0.0",
        "aiosqlite>=0.19.0",
        "pydantic>=2.5.0",
    ],
    entry_points={
        "console_scripts": [
            "clipberry=clipberry.main:main",
        ],
    },
)
