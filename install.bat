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
call "%USERPROFILE%\.poetry\bin\poetry" install

for /f "tokens=1,2" %%a in ('"%USERPROFILE%\.poetry\bin\poetry" env info') do if "%%a" == "Path:" set poetry_env=%%b

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
