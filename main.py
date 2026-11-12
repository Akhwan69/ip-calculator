import sys
import re
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _valid_ip(ip):
    if not isinstance(ip, str) or not ip or " " in ip:
        raise ValueError("IP tidak valid")
    parts = ip.split(".")
    if len(parts) != 4:
        raise ValueError("IP tidak valid")
    for p in parts:
        if not p.isdigit():
            raise ValueError("IP tidak valid")
        if len(p) > 1 and p.startswith("0"):
            raise ValueError("IP tidak valid")
        n = int(p)
        if n < 0 or n > 255:
            raise ValueError("IP tidak valid")


def _ip_to_int(ip):
    o = [int(x) for x in ip.split(".")]
    return (o[0] << 24) | (o[1] << 16) | (o[2] << 8) | o[3]


def _int_to_ip(n):
    return ".".join(str((n >> (8 * i)) & 255) for i in (3, 2, 1, 0))


def hitung_subnet(ip: str, prefix: int) -> dict:
    _valid_ip(ip)
    if not _is_int(prefix) or prefix < 0 or prefix > 32:
        raise ValueError("Prefix tidak valid")

    ip_int = _ip_to_int(ip)
    if prefix == 0:
        mask_int = 0
    else:
        mask_int = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    network_int = ip_int & mask_int
    broadcast_int = network_int | (~mask_int & 0xFFFFFFFF)

    if prefix == 32:
        usable = 1
        first_host = last_host = ip
        broadcast = None
    elif prefix == 31:
        usable = 2
        first_host = _int_to_ip(network_int)
        last_host = _int_to_ip(broadcast_int)
        broadcast = None
    else:
        usable = (1 << (32 - prefix)) - 2
        first_host = _int_to_ip(network_int + 1)
        last_host = _int_to_ip(broadcast_int - 1)
        broadcast = _int_to_ip(broadcast_int)

    return {
        "mask": _int_to_ip(mask_int),
        "network": _int_to_ip(network_int),
        "broadcast": broadcast,
        "first_host": first_host,
        "last_host": last_host,
        "usable_hosts": usable,
    }


def parse_mask2(val):
    if val is None:
        return None
    v = str(val).strip()
    if v == "":
        return None
    if "." in v:
        parts = v.split(".")
        if len(parts) != 4:
            raise ValueError("Netmask tidak valid")
        for p in parts:
            if not p.isdigit():
                raise ValueError("Netmask tidak valid")
            n = int(p)
            if n < 0 or n > 255:
                raise ValueError("Netmask tidak valid")
        n = _ip_to_int(v)
        b = format(n, "032b")
        if not re.fullmatch(r"1*0*", b):
            raise ValueError("Netmask tidak valid")
        return b.count("1")
    if not v.isdigit():
        raise ValueError("Netmask tidak valid")
    p = int(v)
    if p < 0 or p > 32:
        raise ValueError("Netmask tidak valid")
    return p


def _block_host_bits(need):
    bits = 2
    while (1 << bits) - 2 < need:
        bits += 1
    return bits


def alokasi_vlsm(network_cidr: str, kebutuhan_host: list) -> list:
    if not isinstance(network_cidr, str) or "/" not in network_cidr:
        raise ValueError("network_cidr tidak valid")
    ip_part, prefix_part = network_cidr.split("/", 1)
    _valid_ip(ip_part)
    if not prefix_part.isdigit():
        raise ValueError("prefix tidak valid")
    prefix = int(prefix_part)
    if prefix < 0 or prefix > 32:
        raise ValueError("prefix tidak valid")
    base = hitung_subnet(ip_part, prefix)
    if base["network"] != ip_part:
        raise ValueError("bukan alamat jaringan")

    if not isinstance(kebutuhan_host, list) or len(kebutuhan_host) == 0:
        raise ValueError("daftar kebutuhan kosong")
    for h in kebutuhan_host:
        if not _is_int(h) or h < 1:
            raise ValueError("kebutuhan tidak valid")

    current = _ip_to_int(ip_part)
    end = current + (1 << (32 - prefix))
    results = []
    for need in sorted(kebutuhan_host, reverse=True):
        host_bits = _block_host_bits(need)
        block_prefix = 32 - host_bits
        if block_prefix < prefix:
            raise ValueError("blok tidak cukup")
        block_size = 1 << host_bits
        if current % block_size != 0:
            current = ((current + block_size - 1) // block_size) * block_size
        if current + block_size > end:
            raise ValueError("blok tidak cukup menampung")
        block_ip = _int_to_ip(current)
        r = hitung_subnet(block_ip, block_prefix)
        results.append({
            "kebutuhan": need,
            "network_cidr": f"{block_ip}/{block_prefix}",
            "mask": r["mask"],
            "network": r["network"],
            "broadcast": r["broadcast"],
            "first_host": r["first_host"],
            "last_host": r["last_host"],
            "usable_hosts": r["usable_hosts"],
        })
        current += block_size
    return results


def compute_subnets(ip, prefix, prefix2):
    if prefix2 is None or prefix2 == prefix:
        return None
    base = hitung_subnet(ip, prefix)
    network_int = _ip_to_int(base["network"])
    if prefix2 > prefix:
        count = 1 << (prefix2 - prefix)
        block_size = 1 << (32 - prefix2)
        if prefix2 == 32:
            hosts_per = 1
        elif prefix2 == 31:
            hosts_per = 2
        else:
            hosts_per = (1 << (32 - prefix2)) - 2
        total_hosts = count * hosts_per
        MAX = 200
        subnets = []
        for i in range(min(count, MAX)):
            net_int = network_int + i * block_size
            net_ip = _int_to_ip(net_int)
            r = hitung_subnet(net_ip, prefix2)
            subnets.append({
                "network_cidr": f"{net_ip}/{prefix2}",
                "mask": r["mask"],
                "network": r["network"],
                "broadcast": r["broadcast"],
                "first_host": r["first_host"],
                "last_host": r["last_host"],
                "usable_hosts": r["usable_hosts"],
            })
        return {
            "mode": "subnet",
            "prefix2": prefix2,
            "subnet_count": count,
            "hosts_per_subnet": hosts_per,
            "total_hosts": total_hosts,
            "truncated": count > MAX,
            "subnets": subnets,
        }
    mask2_int = (0xFFFFFFFF << (32 - prefix2)) & 0xFFFFFFFF if prefix2 > 0 else 0
    super_net_int = network_int & mask2_int
    super_ip = _int_to_ip(super_net_int)
    r = hitung_subnet(super_ip, prefix2)
    return {
        "mode": "supernet",
        "prefix2": prefix2,
        "subnet_count": 1,
        "hosts_per_subnet": r["usable_hosts"],
        "total_hosts": r["usable_hosts"],
        "truncated": False,
        "subnets": [{
            "network_cidr": f"{super_ip}/{prefix2}",
            "mask": r["mask"],
            "network": r["network"],
            "broadcast": r["broadcast"],
            "first_host": r["first_host"],
            "last_host": r["last_host"],
            "usable_hosts": r["usable_hosts"],
        }],
    }


def _is_private(ip):
    o = [int(x) for x in ip.split(".")]
    if o[0] == 10:
        return True
    if o[0] == 172 and 16 <= o[1] <= 31:
        return True
    if o[0] == 192 and o[1] == 168:
        return True
    return False


def _class_name(first_octet):
    if first_octet <= 127:
        return "Class A"
    if first_octet <= 191:
        return "Class B"
    if first_octet <= 223:
        return "Class C"
    if first_octet <= 239:
        return "Class D"
    return "Class E"


def _fmt_bin(ip, prefix):
    s = ".".join(f"{int(o):08b}" for o in ip.split("."))
    idx = 0
    bits = 0
    for ch in s:
        if bits == prefix:
            break
        if ch == ".":
            idx += 1
            continue
        bits += 1
        idx += 1
    return s[:idx] + " " + s[idx:]


def format_ipcalc(ip, prefix, prefix2=None):
    r = hitung_subnet(ip, prefix)
    mask = r["mask"]
    network = r["network"]
    broadcast = r["broadcast"]
    first = r["first_host"]
    last = r["last_host"]
    usable = r["usable_hosts"]
    wildcard = _int_to_ip((~_ip_to_int(mask)) & 0xFFFFFFFF)
    cls = _class_name(int(ip.split(".")[0]))

    def bn(x):
        return _fmt_bin(x, prefix) if x else ""

    lines = []
    lines.append(f"Address:   {ip:<18} {bn(ip)}")
    lines.append(f"Netmask:   {mask} = {prefix:<2}    {bn(mask)}")
    lines.append(f"Wildcard:  {wildcard:<18} {bn(wildcard)}")
    lines.append("=>")
    lines.append(f"Network:   {network}/{prefix:<2}       {bn(network)} ({cls})")
    if broadcast is None:
        lines.append("Broadcast: (none)")
    else:
        lines.append(f"Broadcast: {broadcast:<18} {bn(broadcast)}")
    lines.append(f"HostMin:   {first:<18} {bn(first)}")
    lines.append(f"HostMax:   {last:<18} {bn(last)}")
    note = " (Private Internet)" if _is_private(ip) else ""
    lines.append(f"Hosts/Net: {usable:<18}{note}".rstrip())

    info = compute_subnets(ip, prefix, prefix2)
    if info is not None:
        lines.append("")
        lines.append("Subnets")
        lines.append("")
        cap = 50
        for sn in info["subnets"][:cap]:
            lines.append(f" Network:   {sn['network']}/{prefix2}  (Hosts/Net: {sn['usable_hosts']})")
        if info["truncated"] or len(info["subnets"]) > cap:
            lines.append(f" ... ({info['subnet_count']} subnets total, showing first {cap})")
        lines.append("")
        lines.append(f"Subnets:   {info['subnet_count']}")
        lines.append(f"Hosts:     {info['total_hosts']}")
    return "\n".join(lines)


class VlsmBody(BaseModel):
    network: str
    kebutuhan_host: list[int]


@app.get("/api/subnet")
def api_subnet(ip: str, prefix: int, mask2: Optional[str] = None):
    try:
        res = hitung_subnet(ip, prefix)
        p2 = parse_mask2(mask2)
        info = compute_subnets(ip, prefix, p2)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    out = {**res, "text": format_ipcalc(ip, prefix, p2)}
    if info is not None:
        out["mask2"] = p2
        out["subnet_count"] = info["subnet_count"]
        out["hosts_per_subnet"] = info["hosts_per_subnet"]
        out["subnets_total_hosts"] = info["total_hosts"]
        out["subnets_truncated"] = info["truncated"]
        out["subnets"] = info["subnets"]
    return out


@app.post("/api/vlsm")
def api_vlsm(body: VlsmBody):
    try:
        res = alokasi_vlsm(body.network, body.kebutuhan_host)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return res


@app.get("/")
def index():
    return FileResponse("index.html")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        print("Usage: python main.py <ip/prefix> [mask2]", file=sys.stderr)
        sys.exit(1)
    if "/" in arg:
        ip, p = arg.split("/", 1)
    else:
        ip = arg
        p = sys.argv[2] if len(sys.argv) > 2 else "24"
    m2 = sys.argv[3] if len(sys.argv) > 3 else None
    print(format_ipcalc(ip, int(p), parse_mask2(m2) if m2 else None))
