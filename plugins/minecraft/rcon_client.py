import asyncio
import struct
from time import monotonic
import logging

logger = logging.getLogger("plugins.minecraft.rcon")

# RCON Packet Types
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0


class RCONError(Exception):
    """Base exception for RCON operations."""
    pass


class RCONAuthenticationError(RCONError):
    """Raised when RCON password authentication fails."""
    pass


class RCONUnavailableError(RCONError):
    """Raised when RCON server is unreachable or exceeds total time budget."""
    pass


def _encode_packet(request_id: int, packet_type: int, payload: str) -> bytes:
    """Encode an RCON protocol packet (Little-Endian 32-bit integers)."""
    payload_bytes = payload.encode("utf-8") + b"\x00\x00"
    length = 4 + 4 + len(payload_bytes)
    return struct.pack("<iii", length, request_id, packet_type) + payload_bytes


async def _read_packet(reader: asyncio.StreamReader) -> tuple[int, int, str]:
    """Read and decode a single RCON packet from the stream."""
    length_header = await reader.readexactly(4)
    length = struct.unpack("<i", length_header)[0]

    packet_data = await reader.readexactly(length)
    request_id, packet_type = struct.unpack("<ii", packet_data[:8])
    payload = packet_data[8:-2].decode("utf-8", errors="replace")
    return request_id, packet_type, payload


async def _send_single_rcon_command(
    host: str,
    port: int,
    password: str,
    command: str,
    timeout: float,
) -> str:
    """Execute a single atomic RCON connection, authentication, and command dispatch."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port),
        timeout=timeout,
    )

    try:
        # 1. Authenticate
        auth_req_id = 1
        auth_packet = _encode_packet(auth_req_id, SERVERDATA_AUTH, password)
        writer.write(auth_packet)
        await asyncio.wait_for(writer.drain(), timeout=timeout)

        resp_id, resp_type, _ = await asyncio.wait_for(_read_packet(reader), timeout=timeout)

        # Some servers send an empty SERVERDATA_RESPONSE_VALUE before AUTH_RESPONSE
        if resp_type == SERVERDATA_RESPONSE_VALUE:
            resp_id, resp_type, _ = await asyncio.wait_for(_read_packet(reader), timeout=timeout)

        if resp_id == -1:
            raise RCONAuthenticationError("RCON authentication failed: invalid password.")

        # 2. Send Command
        cmd_req_id = 2
        cmd_packet = _encode_packet(cmd_req_id, SERVERDATA_EXECCOMMAND, command)
        writer.write(cmd_packet)
        await asyncio.wait_for(writer.drain(), timeout=timeout)

        _, _, response_payload = await asyncio.wait_for(_read_packet(reader), timeout=timeout)
        return response_payload.strip()

    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def execute_rcon_with_budget(
    host: str,
    port: int,
    password: str,
    command: str,
    total_timeout: float = 3.0,
    attempts: int = 2,
) -> str:
    """
    Execute an RCON command using strict Deadline Time Budgeting.
    Every retry attempt is strictly limited to the remaining budget:
    remaining = deadline - monotonic()
    If the deadline expires, raises RCONUnavailableError immediately.
    """
    deadline = monotonic() + total_timeout
    last_error: Exception | None = None

    for attempt in range(attempts):
        remaining = deadline - monotonic()
        if remaining <= 0:
            break

        try:
            return await _send_single_rcon_command(
                host=host,
                port=port,
                password=password,
                command=command,
                timeout=remaining,
            )
        except RCONAuthenticationError:
            # Authentication errors are fatal; retrying is useless
            raise
        except (asyncio.TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            logger.warning(
                f"RCON attempt {attempt + 1}/{attempts} failed to {host}:{port} ({exc}). "
                f"Remaining budget: {max(0.0, deadline - monotonic()):.2f}s"
            )
            if attempt == attempts - 1 or (deadline - monotonic()) <= 0.1:
                break
            # Short backoff, never exceeding the remaining budget
            sleep_duration = min(0.2, max(0.01, deadline - monotonic() - 0.05))
            await asyncio.sleep(sleep_duration)

    raise RCONUnavailableError(
        f"RCON server at {host}:{port} is unavailable or exceeded total time budget of {total_timeout}s: {last_error}"
    )
