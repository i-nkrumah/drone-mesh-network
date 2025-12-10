from dataclasses import dataclass, field
from typing import Tuple, Dict, List
import random


@dataclass
class HelloMsg:
    src: int
    pos: Tuple[float, float, float]
    seq: int


@dataclass
class DVMsg:
    src: int
    vector: Dict[int, Tuple[float, int]]  # dest -> (cost, next_hop_from_src)
    seq: int


@dataclass
class SessionReq:
    """Handshake request from initiator (src) to target (dst)."""
    src: int
    dst: int
    session_id: int
    created_at: float
    path: List[int] = field(default_factory=list)
    hop_count: int = 0


@dataclass
class SessionAck:
    """Handshake ack from target back to initiator."""
    src: int           # target (responder)
    dst: int           # initiator (original src)
    session_id: int
    target: int        # explicit target ID (same as src at creation)
    created_at: float
    path: List[int] = field(default_factory=list)
    hop_count: int = 0


@dataclass
class DataMsg:
    """Actual data packet, created only AFTER handshake succeeds."""
    src: int
    dst: int
    payload: bytes
    created_at: float
    path: List[int] = field(default_factory=list)
    hop_count: int = 0
    id: int = field(default_factory=lambda: random.randint(1, 10_000_000))
