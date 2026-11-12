import pytest
from fastapi.testclient import TestClient

from main import hitung_subnet, alokasi_vlsm, app

client = TestClient(app)


@pytest.mark.parametrize(
    "ip,prefix,exp",
    [
        ("172.16.5.130", 25, {"network": "172.16.5.128", "broadcast": "172.16.5.255", "usable_hosts": 126}),
        ("10.0.0.0", 30, {"network": "10.0.0.0", "broadcast": "10.0.0.3", "usable_hosts": 2}),
        ("192.168.1.0", 31, {"network": "192.168.1.0", "broadcast": None, "usable_hosts": 2}),
        ("192.168.1.5", 32, {"network": "192.168.1.5", "broadcast": None, "usable_hosts": 1}),
    ],
)
def test_hitung_subnet_basic(ip, prefix, exp):
    r = hitung_subnet(ip, prefix)
    for k, v in exp.items():
        assert r[k] == v


@pytest.mark.parametrize("ip,prefix", [
    ("256.1.1.1", 24),
    ("192.168.01.1", 24),
    ("192.168.1", 24),
    ("abc", 24),
    ("", 24),
])
def test_invalid_ip(ip, prefix):
    with pytest.raises(ValueError):
        hitung_subnet(ip, prefix)


@pytest.mark.parametrize("prefix", [33, -1])
def test_invalid_prefix(prefix):
    with pytest.raises(ValueError):
        hitung_subnet("192.168.0.1", prefix)


def test_api_subnet_ok():
    r = client.get("/api/subnet?ip=172.16.5.130&prefix=25")
    assert r.status_code == 200
    assert r.json()["network"] == "172.16.5.128"


def test_api_subnet_invalid():
    r = client.get("/api/subnet?ip=256.1.1.1&prefix=24")
    assert r.status_code == 400
    assert "detail" in r.json()


def test_index():
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()


def test_vlsm():
    r = client.post("/api/vlsm", json={"network": "192.168.1.0/24", "kebutuhan_host": [100, 50, 20, 2]})
    assert r.status_code == 200
    cidrs = [b["network_cidr"] for b in r.json()]
    assert cidrs == ["192.168.1.0/25", "192.168.1.128/26", "192.168.1.192/27", "192.168.1.224/30"]


def test_vlsm_overflow():
    r = client.post("/api/vlsm", json={"network": "192.168.1.0/24", "kebutuhan_host": [200, 100]})
    assert r.status_code == 400


def test_format_contains_sample():
    from main import format_ipcalc
    out = format_ipcalc("192.168.0.1", 24)
    assert "192.168.0.1" in out
    assert "11000000.10101000.00000000 .00000001" in out
    assert "Private Internet" in out
    assert "Class C" in out
