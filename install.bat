@echo off

call :reset_error_level
for /F "tokens=*" %%F in ('python --version') do set result=%%F
if errorlevel 1 goto :please_install_python
if not "%result:~0,8%" == "Python 3" goto :please_update_python
goto :install_other_stuff


:reset_error_level
exit /b 0


:please_update_python
echo Your python installation is too old (version ^< 3).

:please_install_python
echo Please install latest python from here: https://www.python.org/
exit /b 1


:install_other_stuff
call python -m pip install --upgrade pip setuptools wheel
call curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
echo If installation succeeded, please confirm your PATH variable includes these directories:
echo -----------------------------------------------------
echo %USERPROFILE%\AppData\Roaming\Python\Python38\Scripts
echo %USERPROFILE%\.poetry\bin
echo -----------------------------------------------------
echo Be careful - a similar, but not exact path may already be added by python installation.
pause
