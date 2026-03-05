@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 根据脚本目录切换
cd /d "%~dp0"
set "folderName=114514"

REM 获取目标快捷方式对应的实际路径
set "aimShortcut=%folderName%\%~1.lnk"
for /f "tokens=*" %%i in ('powershell -NoProfile -Command ^
    "($w = New-Object -ComObject WScript.Shell).CreateShortcut('%aimShortcut%').TargetPath"') do (
    set "aimPath=%%i"
)

title st - %~1
if "%~1" == "st" (
    set "editor=notepad"
    REM 优先检查 PATH（支持任意安装位置）
    where notepad++ >nul 2>nul && set "editor=notepad++"
    REM 如果 PATH 里没有，再检查默认路径
    if "!editor!" == "notepad" (
        if exist "C:\Program Files\Notepad++\notepad++.exe" set "editor=C:\Program Files\Notepad++\notepad++.exe"
        if exist "C:\Program Files (x86)\Notepad++\notepad++.exe" set "editor=C:\Program Files (x86)\Notepad++\notepad++.exe"
    )
    "!editor!" st.bat

) else if /i "%~1" == "bin" (
    explorer "shell:RecycleBinFolder"

) else if "%~1" == "ls" (
    explorer "%folderName%"
	
) else if /i "%~1" == "env" (
    REM 以管理员权限打开环境变量面板
    powershell -Command "Start-Process rundll32 -ArgumentList 'sysdm.cpl,EditEnvironmentVariables' -Verb RunAs"

) else (
    if "%~2" == "" (
        if exist "%folderName%\%~1.lnk" (
            echo 正在拉起 %~1，路径：!aimPath!
            powershell -NoProfile -Command ^
                "Start-Process -FilePath '%aimPath%'"
        ) else if exist "%folderName%\%~1.url" (
            echo 正在拉起 %~1，路径：%folderName%\%~1.url
            explorer "%folderName%\%~1.url"
        ) else (
            echo 正在拉起 %~1，路径：%~dp0%folderName%\%~1
            powershell -NoProfile -Command ^
                "Start-Process -FilePath '%~dp0%folderName%\%~1'"
        )
    ) else (
        echo 正在搜索 %~2，位置：!aimPath!
        explorer "search-ms:query=%~2&crumb=location:%aimPath%"
    )
)

endlocal
exit /b
