/*
 * Beacon Compatibility Extensions
 * --------------------------------
 * Additional API functions not part of the official Cobalt Strike beacon.h
 * but commonly used by BOF loaders (TrustedSec COFFLoader, etc.)
 *
 * These provide compatibility with BOFs that depend on extended APIs
 * beyond the official Cobalt Strike specification.
 *
 * This file is auto-included by beacon.h - do not include directly.
 */
#ifndef _BEACON_COMPATIBILITY_H_
#define _BEACON_COMPATIBILITY_H_

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Output buffer retrieval - used by some BOFs to read accumulated output */
DECLSPEC_IMPORT char* BeaconGetOutputData(int *outsize);

/* Endianness swap utility */
DECLSPEC_IMPORT uint32_t swap_endianess(uint32_t indata);

#ifdef __cplusplus
}
#endif

#endif // _BEACON_COMPATIBILITY_H_
