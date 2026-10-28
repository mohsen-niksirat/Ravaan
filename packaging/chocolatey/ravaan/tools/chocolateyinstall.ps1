$ErrorActionPreference = 'Stop'

$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url64      = 'https://github.com/mohsen-niksirat/Ravaan/releases/download/v2.4.0/Ravaan-Setup-2.4.0.exe'
$checksum64 = '0000000000000000000000000000000000000000000000000000000000000000'

$packageArgs = @{
  packageName    = 'ravaan'
  unzipLocation  = $toolsDir
  fileType       = 'exe'
  url64bit       = $url64
  checksum64     = $checksum64
  checksumType64 = 'sha256'
  silentArgs     = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /ALLUSERS=0'
  validExitCodes = @(0)
}

Install-ChocolateyPackage @packageArgs
