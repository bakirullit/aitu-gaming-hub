import asyncio
from time import monotonic
import pytest
from plugins.minecraft.rcon_client import (
    execute_rcon_with_budget,
    RCONUnavailableError,
    _encode_packet,
    _read_packet,
    SERVERDATA_AUTH,
)


def test_rcon_packet_encoding() -> None:
    packet = _encode_packet(request_id=42, packet_type=SERVERDATA_AUTH, payload="secret_pass")
    # Body: 4 (req_id) + 4 (type) + 11 (payload len) + 2 (null pad) = 21 bytes
    # Total on-the-wire length including 4-byte length prefix = 25 bytes
    assert len(packet) == 25
    assert packet.endswith(b"\x00\x00")


@pytest.mark.asyncio
async def test_rcon_packet_decoding() -> None:
    packet = _encode_packet(request_id=10, packet_type=2, payload="whitelist on")
    reader = asyncio.StreamReader()
    reader.feed_data(packet)
    reader.feed_eof()

    req_id, p_type, payload = await _read_packet(reader)
    assert req_id == 10
    assert p_type == 2
    assert payload == "whitelist on"


@pytest.mark.asyncio
async def test_rcon_strict_deadline_budget_timeout() -> None:
    """
    Validates that RCON calls strictly enforce total deadline budgeting:
    Total execution time must never exceed total_timeout + small overhead.
    """
    total_budget = 0.4  # 400 milliseconds budget
    start_time = monotonic()

    # Using non-routable TEST-NET-1 IP address (192.0.2.1)
    with pytest.raises(RCONUnavailableError) as exc_info:
        await execute_rcon_with_budget(
            host="192.0.2.1",
            port=25575,
            password="test",
            command="list",
            total_timeout=total_budget,
            attempts=3,
        )

    elapsed = monotonic() - start_time
    assert elapsed < total_budget + 0.25, f"Execution took {elapsed}s, exceeded budget {total_budget}s"
    assert "unavailable or exceeded total time budget" in str(exc_info.value)
