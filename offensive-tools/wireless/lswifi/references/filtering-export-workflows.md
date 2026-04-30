# lswifi Filtering, Export & Event Workflows

## Best Use Cases

- Windows laptop onsite survey
- AP filtering by signal/SSID/BSSID
- event watch for roaming and connectivity changes
- exporting results for offline or scripted analysis

## Practical Filters

```powershell
# strong signals only
lswifi -t -60

# only 6 GHz
lswifi -six

# specific SSID substring
lswifi -include Corp

# specific BSSID
lswifi -bssid 00:11:22:33:44:55
```

## Export Workflows

```powershell
# JSON for scripting
lswifi --json

# CSV for spreadsheet/report workflows
lswifi --csv

# export pcapng representation
lswifi -export
```

## Event Watching

```powershell
lswifi --watchevents
```

Useful for:
- roaming analysis
- intermittent disconnects
- connection state observation

## 6 GHz / RNR Checks

```powershell
lswifi -rnr
```

Use this when multi-band APs and Reduced Neighbor Reports matter.

## Caveat

Windows-native capture through wlanapi is not equivalent to classic monitor-mode packet capture. Use Linux/Kismet/Aircrack workflows when raw frame visibility is required.

## Source Pointers

- Upstream lswifi README and current release line
