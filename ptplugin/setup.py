from setuptools import setup, find_packages

setup(
    name="ptplugin",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["ptplugin"],
    entry_points={"mapproxy": ["pt = ptplugin.pluginmodule"]},
)
