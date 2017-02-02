' This script will generate a file based on specificed template
' Usage: cscript generate_config.vbs
' Example: cscript generate_config.vbs


Const ForReading = 1    
Const ForWriting = 2

' Set up some functions to use later
Set objFSO = CreateObject("Scripting.FileSystemObject")
objStartFolder = objFSO.GetParentFolderName(WScript.ScriptFullName)
Set objFolder = objFSO.GetFolder(objStartFolder)
Set colFiles = objFolder.Files

' Display list of templates in folder, searching for file ending with template.txt
'Wscript.Echo "Templates found in current folder: "

sOut = "Templates found in current folder: " + vbNewLine

For Each objFile in colFiles
  If InStr(objFSO.GetFileName(objFile),"template.txt") Then
    'Wscript.Echo objFile.Name
	sOut = sOut + objFile.Name + vbNewLine
  End If
Next

Wscript.Echo sOut

' Get user input. Note: it is REQUIRED that format is RxSy, otherwise the rest of the script will be meaningless
sTemplate = UserInput( "Enter Template name:" )
Set objFile = objFSO.OpenTextFile(sTemplate, ForReading)
sHostname = UserInput( "Enter Hostname (expected format RxSy):" )

' Strip first letter from the hostname. 
line = Mid(sHostname, 2, Len(sHostname)-1)

' Split the remainder of the line by S. This gives array with 2 values: 0 - the rack number, 1 - the switch number
a = Split(line, "S")

' Apply some logic and figure out the rest of values
If a(1) = "3" Then
  sIP = "xx.xx.xx." + a(0) + " 255.255.255.0"
  sGW = "xx.xx.xx.1"
End If

If a(1) = "1" Then
  sIP = "xx.xx.xx." + a(0) + " 255.255.254.0"
  sGW = "xx.xx.xx.1"
  sKeep_src = "1.1.1.1"
  sKeep_dst = "1.1.1.2"
End If

If a(1) = "2" Then
  sIP = "xx.xx.xx." + a(0) + " 255.255.254.0"
  sGW = "xx.xx.xx.1"
  sKeep_src = "1.1.1.2"  
  sKeep_dst = "1.1.1.1"
End If

sRack = a(0)

' Read file
strText = objFile.ReadAll
objFile.Close

' Replace all the variables. Undeclared variable is empty and doesn't break the script
strNewText = Replace(strText, "%%HOSTNAME%%", sHostname)
strNewText = Replace(strNewText, "%%IPSUBNET%%", sIP)
strNewText = Replace(strNewText, "%%DEFAULTGW%%", sGW)
strNewText = Replace(strNewText, "%%RACK%%", sRack)
strNewText = Replace(strNewText, "%%KPSRC%%", sKeep_src)
strNewText = Replace(strNewText, "%%KPDST%%", sKeep_dst)

sFileName = sHostname + ".txt"

' Write file
Set objFile = objFSO.CreateTextFile(sFileName, ForWriting)
objFile.Write strNewText  'WriteLine adds extra CR/LF
objFile.Close


Function UserInput( myPrompt )
' This function prompts the user for some input.
' When the script runs in CSCRIPT.EXE, StdIn is used,
' otherwise the VBScript InputBox( ) function is used.
' myPrompt is the the text used to prompt the user for input.
' The function returns the input typed either on StdIn or in InputBox( ).
' Written by Rob van der Woude
' http://www.robvanderwoude.com
    ' Check if the script runs in CSCRIPT.EXE
    If UCase( Right( WScript.FullName, 12 ) ) = "\CSCRIPT.EXE" Then
        ' If so, use StdIn and StdOut
        WScript.StdOut.Write myPrompt & " "
        UserInput = WScript.StdIn.ReadLine
    Else
        ' If not, use InputBox( )
        UserInput = InputBox( myPrompt )
    End If
End Function
