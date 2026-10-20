$ErrorActionPreference = 'Stop'

$packageArgs = @{
  packageName  = 'ravaan'
  softwareName = 'Ravaan*'
  silentArgs   = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
}

Uninstall-ChocolateyPackage @packageArgs
