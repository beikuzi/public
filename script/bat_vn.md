[效果演示](README.md) | [拉起指定目录svn图形界面](bat_vn.md) | [快速打开指定目录/软件/链接](bat_st.md)

# 拉起指定目录svn图形界面

步骤：
1. 需要有powershell（一般windows自带，没有就下载
2. 将下面代码保存成vn.bat
3. 创建和folderName相同名字的文件夹，比如下面叫114514
4. 上面两个步骤的脚本和文件放在
C:\Windows\System32
5. win+r输入vn ls，如果上面都正确会打开文件夹目录
6. 将svn发送到桌面快捷方式，重命名成svn，放在文件夹内
7. 将要使用svn的目录，发送桌面快捷方式放到文件夹内，重命名成想要的名字

done

```
@echo off
setlocal enabledelayedexpansion

cd /d %~dp0 
set folderName=114514
set svnShortcut=%folderName%\svn.lnk
set aimShortcut=%folderName%\%~1.lnk
for /f "tokens=*" %%i in ('powershell -Command "$wsh = New-Object -ComObject WScript.Shell; $shortcut = $wsh.CreateShortcut('%svnShortcut%'); $shortcut.TargetPath"') do set svnPath=%%i
for /f "tokens=*" %%i in ('powershell -Command "$wsh = New-Object -ComObject WScript.Shell; $shortcut = $wsh.CreateShortcut('%aimShortcut%'); $shortcut.TargetPath"') do set aimPath=%%i

if "%~1" == "vn" (
    notepad vn.bat
) else if "%~1" == "ls" (
	explorer %folderName%
) else (
    if "%~2" == "cmt" (
        call :LaunchAndFocus "%svnPath%" "/command:commit /path:%aimPath%"
    ) else if "%~2" == "rvt" (
        :: SVN Revert 命令
        call :LaunchAndFocus "%svnPath%" "/command:revert /path:%aimPath%"
    ) else if "%~2" == "clean" (
        :: SVN Cleanup 命令
        call :LaunchAndFocus "%svnPath%" "/command:cleanup /path:%aimPath%"
    ) else if "%~2" == "log" (
        :: SVN Log 命令
        call :LaunchAndFocus "%svnPath%" "/command:log /path:%aimPath%"
    ) else (
        :: SVN Update 命令 (作为默认操作)
        call :LaunchAndFocus "%svnPath%" "/command:update /path:%aimPath%"
    )
)

exit

:: 强制窗口聚焦最前而不是最小化
:LaunchAndFocus
powershell -Command "$p=Start-Process -FilePath '%~1' -ArgumentList '%~2' -PassThru; $p.WaitForInputIdle(); Add-Type -Name 'Win' -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);' -Namespace 'API'; [API.Win]::SetWindowPos($p.MainWindowHandle, [IntPtr]-1, 0, 0, 0, 0, 0x43);"
goto :eof
```