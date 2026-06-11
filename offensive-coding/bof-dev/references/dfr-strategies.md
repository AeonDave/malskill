# DFR (Dynamic Function Resolution) Strategies

**Load when**: Writing Win32 API calls inside a BOF or encountering undefined reference errors (`undefined reference to '__imp_GetProcAddress'`).

## The Concept
Because BOFs are not formally linked to `kernel32.dll` or `ntdll.dll`, the C2 loader must patch the addresses at runtime. 
To instruct the loader, functions must be declared using a specific macro pattern: `Library$Function`.

## 1. DFR Declaration

```c
#include <windows.h>
#include "beacon.h"

// 1. Declare the signature
DECLSPEC_IMPORT HMODULE WINAPI KERNEL32$LoadLibraryA(LPCSTR);
DECLSPEC_IMPORT FARPROC WINAPI KERNEL32$GetProcAddress(HMODULE, LPCSTR);
DECLSPEC_IMPORT BOOL    WINAPI KERNEL32$VirtualProtect(LPVOID, SIZE_T, DWORD, PDWORD);

// 2. Map it (optional but keeps code clean)
#define LoadLibraryA KERNEL32$LoadLibraryA
#define GetProcAddress KERNEL32$GetProcAddress
#define VirtualProtect KERNEL32$VirtualProtect
```

## 2. Advanced: Indirect DFR (Evasion)

If an EDR hooks `LoadLibraryA` or flags the static presence of DFR strings in the `.o` file, do not use DFR. Instead:

1. Locate the PEB (Process Environment Block) manually in assembly (for x64: `__readgsqword(0x60)`).
2. Walk the `InMemoryOrderModuleList` to find your target DLL (e.g., `ntdll.dll`).
3. Parse the Export Directory to resolve function addresses dynamically.
