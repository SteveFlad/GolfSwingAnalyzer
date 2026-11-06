"""
BLE Data Capture Module for Golf Swing Analyzer

This module provides BLE (Bluetooth Low Energy) communication for receiving
quaternion data from the GolfSwingAnalyzer device.

Uses the bleak library for cross-platform BLE support.
"""

import asyncio
import queue
import threading
import time
import re
import platform
from typing import Optional, Callable
from dataclasses import dataclass

_shared_ble_loop = None
_shared_ble_loop_lock = threading.Lock()


def get_or_create_shared_ble_loop() -> asyncio.AbstractEventLoop:
    """Use a single asyncio loop for the BLE stack to avoid Windows bleak loop races."""
    global _shared_ble_loop
    if _shared_ble_loop is None or _shared_ble_loop.is_closed():
        with _shared_ble_loop_lock:
            if _shared_ble_loop is None or _shared_ble_loop.is_closed():
                _shared_ble_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_shared_ble_loop)
    return _shared_ble_loop


try:
    from bleak import BleakClient, BleakScanner
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak not installed. BLE functionality will be disabled.")
    print("Install with: pip install bleak")


@dataclass
class BLEDeviceInfo:
    """Information about a discovered BLE device"""
    name: str
    address: str
    rssi: int = 0
    is_target: bool = False


class BLECapture:
    """BLE data capture with similar interface to SerialCapture"""

    SERVICE_UUID = "12345678-1234-1234-1234-123456789abc"
    CHARACTERISTIC_UUID = "87654321-4321-4321-4321-cba987654321"

    def __init__(
        self,
        device_address: str,
        data_callback: Optional[Callable[[tuple], None]] = None,
        connection_lost_callback: Optional[Callable[[], None]] = None,
    ):
        self.device_address = device_address
        self.data_callback = data_callback
        self.connection_lost_callback = connection_lost_callback

        self.client: Optional[BleakClient] = None
        self.is_running = False
        self.asyncio_loop = None
        self.asyncio_thread = None
        self.parser_thread = None
        self.watchdog_thread = None
        self.message_queue = queue.Queue(maxsize=4096)
        self.queue_overflow_count = 0
        self.parse_error_count = 0
        self.last_data_time = None
        self.data_timeout = 30.0

        self.latest_raw_data = None
        self.calibration_mode = False

        self.quaternion_pattern = re.compile(
            r"Q0:([-\d.]+)\s+Q1:([-\d.]+)\s+Q2:([-\d.]+)\s+Q3:([-\d.]+)"
        )
        self.raw_pattern = re.compile(
            r"RAW\s+AX:([-+]?\d*\.?\d+)\s+AY:([-+]?\d*\.?\d+)\s+AZ:([-+]?\d*\.?\d+)\s+"
            r"GX:([-+]?\d*\.?\d+)\s+GY:([-+]?\d*\.?\d+)\s+GZ:([-+]?\d*\.?\d+)"
        )

    @staticmethod
    async def scan_devices(timeout: float = 5.0) -> list[BLEDeviceInfo]:
        if not BLEAK_AVAILABLE:
            return []

        result = []
        target_uuid = BLECapture.SERVICE_UUID.lower()

        try:
            devices_with_adv = await BleakScanner.discover(timeout=timeout, return_adv=True)
            for _addr, pair in devices_with_adv.items():
                device, adv = pair
                adv_name = getattr(adv, 'local_name', None)
                name = device.name or adv_name or "Unknown"
                address = device.address
                rssi = getattr(device, 'rssi', getattr(adv, 'rssi', 0))
                service_uuids = [u.lower() for u in (getattr(adv, 'service_uuids', None) or [])]
                is_target = (target_uuid in service_uuids) or ("golfswinganalyzer" in name.lower())

                if is_target and name == "Unknown":
                    name = "GolfSwingAnalyzer"

                result.append(BLEDeviceInfo(name=name, address=address, rssi=rssi, is_target=is_target))
        except TypeError:
            devices = await BleakScanner.discover(timeout=timeout)
            for device in devices:
                name = device.name or "Unknown"
                address = device.address
                rssi = getattr(device, 'rssi', 0)
                is_target = "golfswinganalyzer" in name.lower()
                result.append(BLEDeviceInfo(name=name, address=address, rssi=rssi, is_target=is_target))

        if not any(d.is_target for d in result):
            for idx in range(len(result)):
                device = result[idx]
                try:
                    if await BLECapture._device_has_target_service(device.address, timeout=3.0):
                        result[idx].is_target = True
                        if result[idx].name == "Unknown":
                            result[idx].name = "GolfSwingAnalyzer?"
                except Exception:
                    pass

        result.sort(key=lambda d: (d.is_target, d.rssi), reverse=True)
        return result

    @staticmethod
    async def _device_has_target_service(address: str, timeout: float = 4.0) -> bool:
        client_kwargs = {"timeout": timeout}
        device_ref = address
        if platform.system() == "Windows":
            client_kwargs["winrt"] = {"use_cached_services": False}
            try:
                resolved = await BleakScanner.find_device_by_address(address, timeout=max(2.0, timeout))
                if resolved is not None:
                    device_ref = resolved
            except Exception:
                pass

        client = BleakClient(device_ref, **client_kwargs)
        try:
            await client.connect(timeout=timeout)

            if hasattr(client, 'get_services'):
                services_obj = await client.get_services()
            else:
                services_obj = getattr(client, 'services', None)

            if not services_obj:
                return False

            if hasattr(services_obj, 'services') and isinstance(services_obj.services, dict):
                services = list(services_obj.services.values())
            else:
                services = list(services_obj)

            target = BLECapture.SERVICE_UUID.lower().replace('-', '')
            for svc in services:
                svc_uuid = getattr(svc, 'uuid', '')
                if svc_uuid and svc_uuid.lower().replace('-', '') == target:
                    return True
            return False
        finally:
            try:
                if client.is_connected:
                    await client.disconnect()
            except Exception:
                pass

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self.message_queue = queue.Queue(maxsize=4096)
        self.parser_thread = threading.Thread(target=self._parse_loop, daemon=True)
        self.parser_thread.start()
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()
        self.asyncio_thread = threading.Thread(target=self._run_asyncio_loop, daemon=True)
        self.asyncio_thread.start()

    def _run_asyncio_loop(self):
        self.asyncio_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.asyncio_loop)
        try:
            self.asyncio_loop.run_until_complete(self._connect_and_read())
        except Exception as exc:
            print(f"[BLE DIAG] asyncio loop error: {exc}")
        finally:
            try:
                pending = asyncio.all_tasks(loop=self.asyncio_loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.asyncio_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self.asyncio_loop.run_until_complete(self.asyncio_loop.shutdown_asyncgens())
            except Exception:
                pass
            finally:
                self.asyncio_loop.close()

    def _queue_message(self, message: str):
        if not self.is_running:
            return
        self.total_received = getattr(self, 'total_received', 0) + 1
        self.last_data_time = time.time()
        try:
            self.message_queue.put_nowait(message)
        except queue.Full:
            self.queue_overflow_count += 1
            if self.queue_overflow_count <= 5:
                print("[BLE DIAG] message queue overflow; dropping data")

    def _parse_loop(self):
        while self.is_running:
            try:
                message = self.message_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                self._handle_message(message)
            except Exception as exc:
                self.parse_error_count += 1
                if self.parse_error_count <= 5:
                    print(f"[BLE DIAG] parse error: {exc}")
            finally:
                self.message_queue.task_done()

    def _watchdog_loop(self):
        while self.is_running:
            if self.last_data_time is not None:
                seconds_since_data = time.time() - self.last_data_time
                if seconds_since_data > self.data_timeout:
                    print(f"[BLE DIAG] watchdog timeout reached ({seconds_since_data:.1f}s without data)")
                    if self.connection_lost_callback:
                        self.connection_lost_callback("BLE data timeout")
                    self.is_running = False
                    break
            time.sleep(1.0)

    def get_diagnostics(self):
        queue_size = self.message_queue.qsize() if self.message_queue is not None else 0
        return {
            'total_received': self.total_received,
            'total_parsed': self.total_parsed,
            'queue_size': queue_size,
            'queue_overflow_count': self.queue_overflow_count,
            'parse_error_count': self.parse_error_count,
            'last_data_time': self.last_data_time,
            'seconds_since_data': (time.time() - self.last_data_time) if self.last_data_time else None,
        }

    def _handle_message(self, message: str):
        if not message:
            return

        if message.startswith("ERROR:"):
            error_msg = message.replace("ERROR:", "").replace("_", " ")
            print(f"[BLE ERROR] Sensor error: {error_msg}")
            if self.connection_lost_callback:
                self.connection_lost_callback(f"Sensor error: {error_msg}")
            return

        if message.startswith("STATUS:"):
            status_msg = message.replace("STATUS:", "").replace("_", " ")
            print(f"[BLE STATUS] {status_msg}")
            return

        raw_match = self.raw_pattern.search(message)
        if raw_match:
            ax = float(raw_match.group(1))
            ay = float(raw_match.group(2))
            az = float(raw_match.group(3))
            gx = float(raw_match.group(4))
            gy = float(raw_match.group(5))
            gz = float(raw_match.group(6))

            self.total_parsed = getattr(self, 'total_parsed', 0) + 1
            self.latest_raw_data = {
                'accel': [ax, ay, az],
                'gyro': [gx, gy, gz],
                'timestamp': time.time(),
                'type': 'raw'
            }

            if self.data_callback:
                self.data_callback(self.latest_raw_data)
            return

        match = self.quaternion_pattern.search(message)
        if match:
            q0 = float(match.group(1))
            q1 = float(match.group(2))
            q2 = float(match.group(3))
            q3 = float(match.group(4))

            self.total_parsed = getattr(self, 'total_parsed', 0) + 1
            self.latest_raw_data = {
                'q0': q0,
                'q1': q1,
                'q2': q2,
                'q3': q3,
                'timestamp': time.time(),
                'type': 'quaternion'
            }

            if self.data_callback:
                self.data_callback((q0, q1, q2, q3))
            return

        if getattr(self, 'total_parsed', 0) == 0:
            self.parse_error_count += 1

    async def _get_services_with_retry(self, attempts: int = 4, delay_seconds: float = 0.6):
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                if hasattr(self.client, 'get_services'):
                    services_obj = await self.client.get_services()
                else:
                    services_obj = getattr(self.client, 'services', None)

                if not services_obj:
                    raise RuntimeError("No GATT services available yet")

                if hasattr(services_obj, 'services') and isinstance(services_obj.services, dict):
                    services = list(services_obj.services.values())
                else:
                    services = list(services_obj)

                if services:
                    return services
                raise RuntimeError("No GATT services discovered")
            except Exception as e:
                last_error = e
                print(f"Service discovery attempt {attempt}/{attempts} failed: {e}")

            if attempt < attempts:
                await asyncio.sleep(delay_seconds)

        if last_error:
            raise last_error
        raise RuntimeError("No GATT services discovered")

    async def _connect_and_read(self):
        max_retries = 3
        retry_delay = 2
        last_error = None
        connected_once = False

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"BLE connection retry {attempt}/{max_retries}...")
                    await asyncio.sleep(retry_delay)

                print(f"Connecting to BLE device {self.device_address}...")
                device_ref = self.device_address
                client_kwargs = {"timeout": 20.0}

                if platform.system() == "Windows":
                    resolved = await BleakScanner.find_device_by_address(self.device_address, timeout=8.0)
                    if resolved is not None:
                        device_ref = resolved
                    else:
                        print(
                            f"WARNING: Device {self.device_address} not discoverable at connect time; "
                            "trying direct-address connect"
                        )
                    client_kwargs["winrt"] = {"use_cached_services": False}

                self.client = BleakClient(device_ref, **client_kwargs)
                await self.client.connect(timeout=20.0)
                print("BLE physical connection established")

                print("Waiting for GATT service discovery...")
                await asyncio.sleep(1.5)

                print("Enumerating GATT services...")
                try:
                    services = await self._get_services_with_retry()
                    print(f"Found {len(services)} GATT services")

                    service_found = False
                    char_found = False
                    target_service_uuid = self.SERVICE_UUID.lower().replace('-', '')
                    target_char_uuid = self.CHARACTERISTIC_UUID.lower().replace('-', '')

                    for service in services:
                        service_uuid_norm = service.uuid.lower().replace('-', '')
                        if service_uuid_norm == target_service_uuid:
                            service_found = True
                            print(f"[OK] Found GolfSwingAnalyzer service: {service.uuid}")
                            for char in service.characteristics:
                                char_uuid_norm = char.uuid.lower().replace('-', '')
                                print(f"    Characteristic: {char.uuid}")
                                if char_uuid_norm == target_char_uuid:
                                    char_found = True
                                    print("    [OK] Found quaternion data characteristic")
                                    break
                            break

                    if not service_found:
                        print(f"ERROR: Service {self.SERVICE_UUID} not found on device")
                    if not char_found:
                        print(f"ERROR: Characteristic {self.CHARACTERISTIC_UUID} not found")

                    if not service_found or not char_found:
                        await self.client.disconnect()
                        print("ERROR: Device doesn't have required BLE service/characteristic")
                        if self.connection_lost_callback:
                            self.connection_lost_callback("BLE service/characteristic not found")
                        return

                except Exception as e:
                    print(f"ERROR: Failed to enumerate GATT services: {e}")
                    await self.client.disconnect()
                    raise

                await self.client.start_notify(self.CHARACTERISTIC_UUID, self._notification_handler)
                connected_once = True

                print("BLE connected - waiting for data...")
                print("GolfSwingAnalyzer stream active. Showing incoming quaternion/raw messages...")
                self.last_data_time = time.time()

                while self.is_running:
                    await asyncio.sleep(1.0)
                    if self.client is None or not self.client.is_connected:
                        print("BLE connection lost - client disconnected")
                        break

                    if self.last_data_time is not None:
                        time_since_data = time.time() - self.last_data_time
                        if time_since_data > self.data_timeout:
                            print(
                                f"[BLE DIAG] no fresh BLE payload for {time_since_data:.1f}s; "
                                f"treating it as a stalled stream and closing the connection"
                            )
                            break

                if self.client is not None and self.client.is_connected:
                    await self.client.stop_notify(self.CHARACTERISTIC_UUID)
                    await self.client.disconnect()

                return

            except Exception as e:
                last_error = e
                print(f"BLE connection attempt {attempt + 1} failed: {e}")
                error_str = str(e).lower()
                if "unreachable" in error_str:
                    print("HINT: 'Unreachable' error often means device needs pairing")
                elif "timeout" in error_str:
                    print("HINT: Connection timeout - device may be too far or has interference")
                elif "not found" in error_str:
                    print("HINT: Device not found - ensure it's powered on and advertising")

                if self.client:
                    try:
                        await self.client.disconnect()
                    except Exception:
                        pass

                if attempt == max_retries - 1:
                    print(f"BLE connection failed after {max_retries} attempts")
                    if self.connection_lost_callback:
                        if last_error:
                            self.connection_lost_callback(f"BLE connect error: {last_error}")
                        else:
                            self.connection_lost_callback("BLE connection failed after retries")

        if self.connection_lost_callback and self.is_running and connected_once:
            self.connection_lost_callback("BLE connection lost")

    def _notification_handler(self, sender, data: bytearray):
        try:
            message = data.decode('utf-8', errors='ignore').strip()
            self._queue_message(message)
        except Exception as exc:
            self.parse_error_count += 1
            if self.parse_error_count <= 5:
                print(f"[BLE DIAG] notification decode error: {exc}")

    def is_connected(self):
        return self.is_running and self.client is not None and (self.client.is_connected if hasattr(self.client, 'is_connected') else False)

    def stop(self):
        self.is_running = False
        if self.asyncio_loop and self.asyncio_loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self._disconnect_client(), self.asyncio_loop)
                future.result(timeout=2.0)
            except Exception:
                pass
        if self.parser_thread:
            self.parser_thread.join(timeout=2.0)
        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=2.0)
        if self.asyncio_thread:
            self.asyncio_thread.join(timeout=2.0)

    def get_stats(self):
        parse_rate = 0.0
        if self.total_received > 0:
            parse_rate = (self.total_parsed / self.total_received) * 100

        return {
            'total_received': self.total_received,
            'total_parsed': self.total_parsed,
            'parse_rate': parse_rate,
            'last_data_time': self.last_data_time,
            'seconds_since_data': (time.time() - self.last_data_time) if self.last_data_time else None
        }

    def enable_calibration_mode(self):
        if self.is_connected() and self.client:
            self.calibration_mode = True
            self.latest_raw_data = None
            asyncio.run_coroutine_threadsafe(
                self.client.write_gatt_char(self.CHARACTERISTIC_UUID, b"CAL_START"),
                self.asyncio_loop
            )
            print("[CAL DEBUG] BLE: Calibration mode enabled - CAL_START sent")
            return True
        print("[CAL DEBUG] BLE: Could not enable calibration - not connected")
        return False

    def disable_calibration_mode(self):
        if self.is_connected() and self.client:
            self.calibration_mode = False
            asyncio.run_coroutine_threadsafe(
                self.client.write_gatt_char(self.CHARACTERISTIC_UUID, b"CAL_STOP"),
                self.asyncio_loop
            )
            print("[CAL DEBUG] BLE: Calibration mode disabled - CAL_STOP sent")
            return True
        return False

    def get_latest_raw_data(self):
        return self.latest_raw_data

    async def _disconnect_client(self):
        if self.client and self.client.is_connected:
            try:
                await self.client.stop_notify(self.CHARACTERISTIC_UUID)
            except Exception:
                pass
            try:
                await self.client.disconnect()
            except Exception:
                pass


# Synchronous wrapper for device scanning
def scan_ble_devices_sync(timeout: float = 5.0) -> list[BLEDeviceInfo]:
    if not BLEAK_AVAILABLE:
        return []

    loop = get_or_create_shared_ble_loop()
    try:
        return loop.run_until_complete(BLECapture.scan_devices(timeout))
    finally:
        asyncio.set_event_loop(loop)


async def main():
    print("Scanning for BLE devices...")
    devices = await BLECapture.scan_devices(timeout=5.0)

    if not devices:
        print("No devices found")
        return

    print(f"\nFound {len(devices)} device(s):")
    for i, device in enumerate(devices, 1):
        print(f"  {i}. {device.name} ({device.address}) RSSI: {device.rssi} dBm")

        if "XIAO" in device.name.upper() or "ESP32" in device.name.upper():
            print(f"     ^ This looks like an ESP32 device!")

    preferred_targets = [
        d for d in devices
        if any(token in d.name.lower() for token in ("golf", "esp32", "xiao", "gsa"))
    ]
    if not preferred_targets:
        preferred_targets = devices

    selected = preferred_targets[0]
    print(f"\nConnecting to {selected.name} ({selected.address})...")

    def on_data(data):
        if isinstance(data, tuple) and len(data) == 4:
            q0, q1, q2, q3 = data
            print(f"Quaternion: Q0={q0:.6f} Q1={q1:.6f} Q2={q2:.6f} Q3={q3:.6f}")
        elif isinstance(data, dict):
            if data.get('type') == 'raw':
                accel = data.get('accel', [0.0, 0.0, 0.0])
                gyro = data.get('gyro', [0.0, 0.0, 0.0])
                print(f"RAW: AX={accel[0]:.3f} AY={accel[1]:.3f} AZ={accel[2]:.3f} GX={gyro[0]:.3f} GY={gyro[1]:.3f} GZ={gyro[2]:.3f}")
            elif data.get('type') == 'quaternion':
                print(
                    f"Quaternion: Q0={data['q0']:.6f} Q1={data['q1']:.6f} "
                    f"Q2={data['q2']:.6f} Q3={data['q3']:.6f}"
                )

    def on_disconnect():
        print("Connection lost!")

    capture = BLECapture(selected.address, on_data, on_disconnect)
    capture.data_timeout = 12.0
    try:
        capture.start()
        try:
            await capture._connect_and_read()
        except asyncio.TimeoutError:
            print("[BLE DIAG] outer timeout reached; the BLE session was closed cleanly instead of crashing.")
        except Exception as exc:
            print(f"[BLE DIAG] BLE session ended with exception: {exc}")
            raise
    finally:
        capture.is_running = False
        if capture.client and capture.client.is_connected:
            await capture.client.disconnect()
        capture.stop()


if __name__ == "__main__":
    asyncio.run(main())
