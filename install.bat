@echo off


call :reset_variables


for /f "tokens=*" %%a in ('python --version') do set python_version=%%a
if errorlevel 1 goto :please_install_python
if not "%python_version:~0,8%" == "Python 3" goto :please_update_python
goto :install_other_stuff


:reset_variables
set python_version=None
set poetry_env=None
exit /b 0


:please_update_python
echo Your python installation is too old (version ^< 3).

:please_install_python
echo Please install latest python from here: https://www.python.org/
exit /b 1


:install_other_stuff
call python -m pip install --upgrade pip setuptools wheel
call curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python


:stuff_that_no_longer_needs_to_be_repeated_as_project_is_configured_already
:: First, I initialized the project by calling "poetry new sahyun-bot" outside of the folder of this project.
:: This created the basic structure. I cleaned it up by removing __init__.py files (not sure if they are useful).
:: I also changed README file extension to '.md' as that is what I am used to.
::
:: My IDE does not have explicit support for poetry yet, so I had to manually configure the virtual environment.
:: I called 'poetry show' which initialized it. This is not needed in the script, since 'poetry install' does the
:: same thing.
::
:: I still had to configure the environment. To do so, I had to set the interpreter for the project to the one
:: inside the environment directory. This directory is printed by this script, with the remaining instructions.
::
:: I added git repository using an IDE. I manually created the '.gitignore' file and started adding things to it.
:: I also manually created LICENSE and TODO files.
::
:: I manually updated 'pyproject.toml' file by using instructions from https://python-poetry.org/docs/pyproject/
:: Since the default initialization was missing various parameters which were reflected in the .egg-info files.
::
:: Finally, I added all dependencies that I wanted to use with 'poetry add <name>'. This also installed the
:: dependencies in the environment.


:prepare_environment
call "%USERPROFILE%\.poetry\bin\poetry" install
for /f "tokens=*" %%a in ('"%USERPROFILE%\.poetry\bin\poetry" env info --path') do set poetry_env=%%a


:print_any_remaining_instructions
echo -----------------------------------------------------
echo If the installations succeeded, please confirm your PATH variable includes the following directories.
echo Be careful - a similar, but not exact path may already be added by python installation.
echo -----------------------------------------------------
echo %USERPROFILE%\AppData\Roaming\Python\Python38\Scripts
echo %USERPROFILE%\.poetry\bin
echo -----------------------------------------------------
echo Finally, if you are using an IDE which needs manual virtual environment setup, the following is the directory.
echo -----------------------------------------------------
echo %poetry_env%
echo -----------------------------------------------------
pause
