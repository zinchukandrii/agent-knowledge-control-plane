#requires -RunAsAdministrator
<#!
.SYNOPSIS
Expose the local fixture-only dashboard to this computer's local Wi-Fi subnet.

.DESCRIPTION
WSL2 uses a NAT address that can change after a restart. This script refreshes
Windows port forwarding for the current WSL address and opens only TCP 8017 on
Private and Public profiles, restricted to LocalSubnet.
#>

param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8017
)

$ruleName = "AndriiDev Local Demo $Port"
$wslAddresses = ((wsl.exe hostname -I).Trim() -split '\s+')
$wslIp = $wslAddresses | Where-Object { $_ -notlike '172.17.*' } | Select-Object -First 1
$lanIp = (Get-NetIPConfiguration |
    Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
    ForEach-Object { $_.IPv4Address.IPAddress } |
    Select-Object -First 1)

if (-not $wslIp -or -not $lanIp) {
    throw "Could not resolve the active WSL or LAN IPv4 address."
}

Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
netsh interface portproxy delete v4tov4 "listenport=$Port" "listenaddress=0.0.0.0" | Out-Null
netsh interface portproxy add v4tov4 "listenport=$Port" "listenaddress=0.0.0.0" "connectport=$Port" "connectaddress=$wslIp"
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private,Public -RemoteAddress LocalSubnet | Out-Null

Write-Host "LAN dashboard ready: http://$lanIp`:$Port/"
Write-Host "WSL target: $wslIp`:$Port | Firewall: Private/Public + LocalSubnet only"
