from setuptools import setup, find_packages

setup(
    name="smartbusiners",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "smartbusiners.gui": ["static/*"],
    },
    install_requires=[
        "typer[all]>=0.12.0",
        "rich>=13.7.1",
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.28.0",
        "websockets>=12.0",
        "pydantic>=2.6.4",
        "pydantic-settings>=2.2.1",
        "google-genai>=0.1.1",
        "requests>=2.31.0",
        "python-dotenv>=1.0.1",
        "aiofiles>=23.2.1",
    ],
    entry_points={
        "console_scripts": [
            "smartbusiners=smartbusiners.cli:app",
            "smartbusiners-gui=smartbusiners.gui.server:main",
        ],
    },
)
