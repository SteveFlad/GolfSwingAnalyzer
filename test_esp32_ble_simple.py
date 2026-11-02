"""Robust ESP32 BLE sanity test for GolfSwingAnalyzer firmware.

Avoids hard-coded MAC address assumptions and checks for expected GATT UUIDs.
"""
import asyncio
import platform
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
CHAR_UUID = "87654321-4321-4321-4321-cba987654321"
NAME_HINT = "golfswinganalyzer"
TEST_VERSION = "v2-uuid-probe"


def _normalize_uuid(value: str) -> str:
    return (value or "").lower().replace("-", "")


async def _get_services(client):
    if hasattr(client, "get_services"):
        services_obj = await client.get_services()
    else:
        services_obj = getattr(client, "services", None)

    if not services_obj:
        return []

    if hasattr(services_obj, "services") and isinstance(services_obj.services, dict):
        return list(services_obj.services.values())
    return list(services_obj)


async def _probe_device(address: str, timeout: float = 8.0):
    winrt_opts = {"use_cached_services": False} if platform.system() == "Windows" else None
    kwargs = {"timeout": timeout}
    if winrt_opts:
        kwargs["winrt"] = winrt_opts

    async with BleakClient(address, **kwargs) as client:
        if not client.is_connected:
            return False, "Connected flag was false", []

        services = await _get_services(client)
        target_service = _normalize_uuid(SERVICE_UUID)
        target_char = _normalize_uuid(CHAR_UUID)

        found_service = False
        found_char = False
        discovered = []

        for svc in services:
            svc_uuid = getattr(svc, "uuid", "")
            discovered.append(svc_uuid)
            if _normalize_uuid(svc_uuid) == target_service:
                found_service = True
                for ch in svc.characteristics:
                    if _normalize_uuid(getattr(ch, "uuid", "")) == target_char:
                        found_char = True
                        break

        if found_service and found_char:
            return True, "Target service/characteristic found", discovered
        if found_service:
            return False, "Target service found but characteristic missing", discovered
        return False, "Target service UUID not found", discovered


async def test_connection():
    print("=" * 60)
    print(f"ESP32 BLE Hardware Test ({TEST_VERSION})")
    print("=" * 60)

    print("\n1. Scanning for BLE devices (with advertisement data)...")
    devices = []
    try:
        discovered = await BleakScanner.discover(timeout=6.0, return_adv=True)
        for _addr, pair in discovered.items():
            device, adv = pair
            name = (device.name or getattr(adv, "local_name", None) or "Unknown")
            address = device.address
            rssi = getattr(device, "rssi", getattr(adv, "rssi", "N/A"))
            adv_uuids = [u.lower() for u in (getattr(adv, "service_uuids", None) or [])]
            looks_like_target = (NAME_HINT in name.lower()) or (_normalize_uuid(SERVICE_UUID) in [_normalize_uuid(u) for u in adv_uuids])
            devices.append((address, name, rssi, looks_like_target))
    except TypeError:
        # Older bleak without return_adv support.
        fallback = await BleakScanner.discover(timeout=6.0)
        for d in fallback:
            name = d.name or "Unknown"
            address = d.address
            rssi = getattr(d, "rssi", "N/A")
            looks_like_target = NAME_HINT in name.lower()
            devices.append((address, name, rssi, looks_like_target))

    if not devices:
        print("✗ No BLE devices found at all")
        return False

    devices.sort(key=lambda row: (row[3], row[2] if isinstance(row[2], int) else -999), reverse=True)
    print(f"Found {len(devices)} BLE device(s):")
    for addr, name, rssi, is_target in devices:
        marker = " [LIKELY GSA]" if is_target else ""
        print(f"  - {name} ({addr}) RSSI:{rssi}{marker}")

    print("\n2. Probing candidates for GolfSwingAnalyzer GATT service...")
    probe_order = [d for d in devices if d[3]] + [d for d in devices if not d[3]]
    probe_limit = min(8, len(probe_order))

    for idx in range(probe_limit):
        addr, name, rssi, _ = probe_order[idx]
        print(f"\n  Probe {idx + 1}/{probe_limit}: {name} ({addr}) RSSI:{rssi}")
        try:
            ok, reason, discovered_services = await _probe_device(addr, timeout=8.0)
            if ok:
                print("  ✓ Connected and validated expected GATT UUIDs")
                print(f"  ✓ Target address: {addr}")
                return True
            print(f"  ✗ Not target device: {reason}")
            if discovered_services:
                print(f"    Services seen: {len(discovered_services)}")
        except Exception as e:
            print(f"  ✗ Probe failed: {e}")

    print("\n✗ Could not find expected GolfSwingAnalyzer GATT service on scanned devices")
    print("  This does not prove hardware failure; it indicates discoverability or firmware advertising mismatch.")
    return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    print("\n" + "=" * 60)
    if result:
        print("VERDICT: BLE hardware path is functional")
        print("Issue is likely app-side device selection or connection workflow")
    else:
        print("VERDICT: GolfSwingAnalyzer BLE service not discovered")
        print("Likely causes: firmware advertising visibility, Windows BLE stack cache, or wrong board in range")
    print("=" * 60)
