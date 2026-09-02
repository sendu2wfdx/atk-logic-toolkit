from __future__ import annotations

DL16_VENDOR_ID = 0x1A86
DL16_PRODUCT_ID = 0xFFCC


def usb_backend():
    """Return the bundled libusb backend on Windows when available."""
    try:
        import libusb_package
        return libusb_package.get_libusb1_backend()
    except ImportError:
        return None


def scan() -> list[dict]:
    try:
        import usb.core
        import usb.util
    except ImportError as exc:
        raise RuntimeError("USB scan requires PyUSB; install with: pip install 'alientek-dl16-toolkit[usb]'") from exc
    devices = []
    for dev in usb.core.find(find_all=True, idVendor=DL16_VENDOR_ID, idProduct=DL16_PRODUCT_ID, backend=usb_backend()) or []:
        item = {"model": "DL16", "vid": f"0x{dev.idVendor:04x}", "pid": f"0x{dev.idProduct:04x}", "bus": getattr(dev, "bus", None), "address": getattr(dev, "address", None)}
        for field, index in (("manufacturer", dev.iManufacturer), ("product", dev.iProduct), ("serial", dev.iSerialNumber)):
            try:
                item[field] = usb.util.get_string(dev, index) if index else None
            except Exception:
                item[field] = None
        devices.append(item)
    return devices
