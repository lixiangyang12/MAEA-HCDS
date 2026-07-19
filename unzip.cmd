@echo off
REM unzip wrapper for Windows using PowerShell Expand-Archive
REM Usage: unzip -qo "file.zip" -d "destination"

setlocal enabledelayedexpansion

set "ZIPFILE="
set "DEST="
set "QUIET=0"
set "OVERWRITE=0"

:parse
if "%~1"=="" goto run
if /i "%~1"=="-q" (set "QUIET=1" & shift & goto parse)
if /i "%~1"=="-qo" (set "QUIET=1" & set "OVERWRITE=1" & shift & goto parse)
if /i "%~1"=="-o" (set "OVERWRITE=1" & shift & goto parse)
if /i "%~1"=="-d" (
    shift
    set "DEST=%~1"
    shift
    goto parse
)
if "%~1"=="-q" (
    set "QUIET=1"
) else (
    if not defined ZIPFILE (
        set "ZIPFILE=%~1"
    )
)
shift
goto parse

:run
if not defined ZIPFILE (
    echo Error: No zip file specified
    exit /b 1
)

if not defined DEST set "DEST=."

if not exist "%ZIPFILE%" (
    echo Error: File not found: %ZIPFILE%
    exit /b 1
)

REM Use PowerShell Expand-Archive
powershell -NoProfile -Command "Expand-Archive -Path '%ZIPFILE%' -DestinationPath '%DEST%' -Force"

if %ERRORLEVEL%==0 (
    exit /b 0
) else (
    exit /b 1
)
