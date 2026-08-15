@echo off  
if not exist \" "dist\\x\ goto :no_portable  ;
goto :has_portable  ;
:no_portable  ;
echo missing  ;
:has_portable  ;
