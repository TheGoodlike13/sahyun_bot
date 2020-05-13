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
:: I called 'poetry show' which initialized it. This is not needed in the script, since 'poetry install' also does it.
::
:: I still had to configure the environment in the IDE. To do so, I had to set the interpreter for the project to the
:: one inside the environment directory. This directory is printed by this script, with the remaining instructions.
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
if not exist "config.ini" call xcopy empty_config.ini config.ini* /q


:print_any_remaining_instructions
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo -------------------------------------------------------------------------------
echo Verify that your PATH variables include the following directories.
echo Make sure they are exact, as similar ones may be added by Python installer.
echo -------------------------------------------------------------------------------
echo %USERPROFILE%\AppData\Roaming\Python\Python38\Scripts
echo %USERPROFILE%\.poetry\bin
echo -------------------------------------------------------------------------------
echo Virtual environment can be found in the following directory.
echo -------------------------------------------------------------------------------
echo %poetry_env%
echo -------------------------------------------------------------------------------
echo Review 'config.ini' file. README.md should help explain what is expected.
echo -------------------------------------------------------------------------------
pause
exit /b 0


:other_stuff_I_did_that_is_not_directly_related_to_the_project
:: I had to manually edit an internal PyCharm file. Since I am using Python 3.8, and my PyCharm version is outdated,
:: when opening the Python Console, I would receive the following error:
::
:: TypeError: an integer is required (got type bytes)
::
:: This error occurred in the '_compat.py' file. It was supposed to be fixed for a later PyCharm version.
:: The exact fix can be found here:
:: https://github.com/JetBrains/intellij-community/commit/07ef928f3b1fbc24401380110691342a558de242
::
:: To easily run & debug the files, I changed the default Python run configuration. First, I always launch in
:: Python Console for maximum flexibility. Second, I set the working directory to project directory. This way
:: I can use the 'config.ini' file there without issues.
::
:: I cannot run some debug configurations with PyCharm. They hang when I enter a command with a breakpoint.
:: However, if I run them normally first, THEN attach the debugger in Python Console, it works like a charm.
::
:: I use pytest for testing. Running tests, however, produces a '.pytest_cache' folder in the directory. This is
:: annoying as fuck, even if they are ignored by git automatically. To avoid this, I modified my pytest run
:: configuration template to always use the project directory as working directory.
