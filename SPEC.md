# SPEC.md

## Tujuan
Kalkulator Subnet IPv4 berbasis web (FastAPI) + CLI dengan output gaya ipcalc (jodies.de/ipcalc), port 8086.

## Aturan Validasi
- IP: tepat 4 oktet, tiap oktet 0-255, tanpa leading zero, tanpa spasi.
- Prefix: bilangan bulat 0-32.
- Input tidak valid: raise ValueError -> HTTP 400 dengan field "detail".

## Kontrak Fungsi
- `hitung_subnet(ip, prefix) -> dict`: kunci mask, network, broadcast, first_host, last_host, usable_hosts.
  - /31: RFC 3021, 2 host, broadcast None.
  - /32: 1 host, broadcast None, first_host=last_host=IP.
  - lainnya: 2^(32-prefix)-2 host.
  - network = IP AND mask (bitwise).
- `alokasi_vlsm(network_cidr, kebutuhan_host) -> list[dict]`: urut kebutuhan desc, blok pangkat 2 terkecil >= need+2 (min /30), raise ValueError bila invalid/tidak muat.

## Kontrak API
- GET /api/subnet?ip=&prefix=
- POST /api/vlsm body {network, kebutuhan_host}
- GET / -> index.html

## Output ipcalc
Address/Netmask/Wildcard/Network/Broadcast/HostMin/HostMax/Hosts/Net dengan binary split pada boundary prefix, wildcard, class, private/public note.

## Di Luar Cakupan
- IPv6, autentikasi.
