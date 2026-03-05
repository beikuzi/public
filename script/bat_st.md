[效果演示](README.md) | [拉起指定目录svn图形界面](bat_vn.md) | [快速打开指定目录/软件/链接](bat_st.md)

# 快速打开指定目录/软件/链接

步骤：
1. 需要有powershell（一般windows自带，没有就下载
2. 将下面代码保存成st.bat
3. 创建和folderName相同名字的文件夹，比如下面叫114514
4. 上面两个步骤的脚本和文件放在
C:\Windows\System32
5. win+r输入st ls，如果上面都正确会打开文件夹目录
6. 创建想要的快捷方式放入文件夹内，支持软件快捷、文件夹快捷、url链接

done

```
@echo off
setlocal enabledelayedexpansion

cd /d %~dp0
set folderName=114514

set aimShortcut=%folderName%\%~1.lnk
for /f "tokens=*" %%i in ('powershell -Command "$wsh = New-Object -ComObject WScript.Shell; $shortcut = $wsh.CreateShortcut('%aimShortcut%'); $shortcut.TargetPath"') do set aimPath=%%i

if "%~1" == "st" (
	notepad st.bat
) else if "%~1" == "ls" (
	explorer %folderName%
) else (
	if "%~2" == "" (
		if exist "%folderName%\%~1.lnk" (
			start "" "%folderName%\%~1.lnk"
		) else if exist "%folderName%\%~1.url" (
			start "" "%folderName%\%~1.url"
		) else (
			start %folderName%\%~1
		)
	) else (
		explorer "search-ms:query=%~2&crumb=location:%aimPath%"
	)
)

endlocal 
exit
```