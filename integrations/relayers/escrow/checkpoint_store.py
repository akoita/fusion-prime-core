"""
Checkpoint store for event relayer
Tracks processed blocks and events to enable restarts and replay protection
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    delete,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()


class CheckpointRecord(Base):
    """SQLAlchemy model for checkpoint persistence"""

    __tablename__ = "relayer_checkpoints"

    chain_id = Column(String, primary_key=True)
    contract_address = Column(String, primary_key=True)
    last_processed_block = Column(Integer, nullable=False)
    last_processed_timestamp = Column(DateTime, nullable=False)
    total_events_processed = Column(Integer, default=0)
    event_metadata = Column(JSON, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (Index("idx_chain_contract", "chain_id", "contract_address"),)


class ProcessedEventRecord(Base):
    """SQLAlchemy model for tracking processed events (replay protection)"""

    __tablename__ = "relayer_processed_events"

    event_id = Column(String, primary_key=True)  # Format: {chain_id}:{tx_hash}:{log_index}
    chain_id = Column(String, nullable=False)
    contract_address = Column(String, nullable=False)
    block_number = Column(Integer, nullable=False)
    transaction_hash = Column(String, nullable=False)
    log_index = Column(Integer, nullable=False)
    event_name = Column(String, nullable=False)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    published = Column(Boolean, default=False)
    event_metadata = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_chain_block", "chain_id", "block_number"),
        Index("idx_tx_hash", "transaction_hash"),
    )


@dataclass
class Checkpoint:
    """Checkpoint data structure"""

    chain_id: str
    contract_address: str
    last_processed_block: int
    last_processed_timestamp: datetime
    total_events_processed: int = 0
    event_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessedEvent:
    """Processed event data structure"""

    event_id: str
    chain_id: str
    contract_address: str
    block_number: int
    transaction_hash: str
    log_index: int
    event_name: str
    processed_at: datetime
    published: bool = False
    event_metadata: Optional[Dict[str, Any]] = None


class CheckpointStore(ABC):
    """Abstract checkpoint store interface"""

    @abstractmethod
    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint"""
        pass

    @abstractmethod
    async def get_checkpoint(self, chain_id: str, contract_address: str) -> Optional[Checkpoint]:
        """Retrieve checkpoint for a contract"""
        pass

    @abstractmethod
    async def mark_event_processed(self, event: ProcessedEvent) -> bool:
        """Mark an event as processed. Returns True if newly marked, False if already processed."""
        pass

    @abstractmethod
    async def is_event_processed(self, event_id: str) -> bool:
        """Check if an event has been processed"""
        pass

    @abstractmethod
    async def get_processed_events(
        self, chain_id: str, from_block: int, to_block: int
    ) -> List[ProcessedEvent]:
        """Get all processed events in a block range"""
        pass

    @abstractmethod
    async def cleanup_old_events(self, before_timestamp: datetime) -> int:
        """Remove old processed events. Returns count of removed events."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the store"""
        pass


class SQLiteCheckpointStore(CheckpointStore):
    """SQLite-based checkpoint store for local development"""

    def __init__(self, db_path: str = "relayer_checkpoints.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Ensure database is initialized"""
        if self._initialized:
            return

        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        # Create tables
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relayer_checkpoints (
                chain_id TEXT NOT NULL,
                contract_address TEXT NOT NULL,
                last_processed_block INTEGER NOT NULL,
                last_processed_timestamp TEXT NOT NULL,
                total_events_processed INTEGER DEFAULT 0,
                event_metadata TEXT,
                updated_at TEXT,
                PRIMARY KEY (chain_id, contract_address)
            )
        """
        )

        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relayer_processed_events (
                event_id TEXT PRIMARY KEY,
                chain_id TEXT NOT NULL,
                contract_address TEXT NOT NULL,
                block_number INTEGER NOT NULL,
                transaction_hash TEXT NOT NULL,
                log_index INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                published INTEGER DEFAULT 0,
                event_metadata TEXT
            )
        """
        )

        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chain_block ON relayer_processed_events(chain_id, block_number)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tx_hash ON relayer_processed_events(transaction_hash)"
        )

        await self._conn.commit()
        self._initialized = True

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        await self._ensure_initialized()
        assert self._conn is not None

        await self._conn.execute(
            """
            INSERT INTO relayer_checkpoints
            (chain_id, contract_address, last_processed_block, last_processed_timestamp,
             total_events_processed, event_metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chain_id, contract_address)
            DO UPDATE SET
                last_processed_block = excluded.last_processed_block,
                last_processed_timestamp = excluded.last_processed_timestamp,
                total_events_processed = excluded.total_events_processed,
                event_metadata = excluded.event_metadata,
                updated_at = excluded.updated_at
        """,
            (
                checkpoint.chain_id,
                checkpoint.contract_address,
                checkpoint.last_processed_block,
                checkpoint.last_processed_timestamp.isoformat(),
                checkpoint.total_events_processed,
                (json.dumps(checkpoint.event_metadata) if checkpoint.event_metadata else None),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._conn.commit()

        logger.info(
            f"Saved checkpoint: {checkpoint.chain_id}:{checkpoint.contract_address} @ block {checkpoint.last_processed_block}"
        )

    async def get_checkpoint(self, chain_id: str, contract_address: str) -> Optional[Checkpoint]:
        await self._ensure_initialized()
        assert self._conn is not None

        cursor = await self._conn.execute(
            """
            SELECT chain_id, contract_address, last_processed_block, last_processed_timestamp,
                   total_events_processed, event_metadata
            FROM relayer_checkpoints
            WHERE chain_id = ? AND contract_address = ?
        """,
            (chain_id, contract_address),
        )

        row = await cursor.fetchone()
        if not row:
            return None

        return Checkpoint(
            chain_id=row["chain_id"],
            contract_address=row["contract_address"],
            last_processed_block=row["last_processed_block"],
            last_processed_timestamp=datetime.fromisoformat(row["last_processed_timestamp"]),
            total_events_processed=row["total_events_processed"],
            event_metadata=(json.loads(row["event_metadata"]) if row["event_metadata"] else None),
        )

    async def mark_event_processed(self, event: ProcessedEvent) -> bool:
        await self._ensure_initialized()
        assert self._conn is not None

        try:
            await self._conn.execute(
                """
                INSERT INTO relayer_processed_events
                (event_id, chain_id, contract_address, block_number, transaction_hash,
                 log_index, event_name, processed_at, published, event_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.chain_id,
                    event.contract_address,
                    event.block_number,
                    event.transaction_hash,
                    event.log_index,
                    event.event_name,
                    event.processed_at.isoformat(),
                    1 if event.published else 0,
                    json.dumps(event.event_metadata) if event.event_metadata else None,
                ),
            )
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            # Already processed
            return False

    async def is_event_processed(self, event_id: str) -> bool:
        await self._ensure_initialized()
        assert self._conn is not None

        cursor = await self._conn.execute(
            "SELECT 1 FROM relayer_processed_events WHERE event_id = ?", (event_id,)
        )
        row = await cursor.fetchone()
        return row is not None

    async def get_processed_events(
        self, chain_id: str, from_block: int, to_block: int
    ) -> List[ProcessedEvent]:
        await self._ensure_initialized()
        assert self._conn is not None

        cursor = await self._conn.execute(
            """
            SELECT event_id, chain_id, contract_address, block_number, transaction_hash,
                   log_index, event_name, processed_at, published, event_metadata
            FROM relayer_processed_events
            WHERE chain_id = ? AND block_number BETWEEN ? AND ?
            ORDER BY block_number, log_index
        """,
            (chain_id, from_block, to_block),
        )

        rows = await cursor.fetchall()
        return [
            ProcessedEvent(
                event_id=row["event_id"],
                chain_id=row["chain_id"],
                contract_address=row["contract_address"],
                block_number=row["block_number"],
                transaction_hash=row["transaction_hash"],
                log_index=row["log_index"],
                event_name=row["event_name"],
                processed_at=datetime.fromisoformat(row["processed_at"]),
                published=bool(row["published"]),
                event_metadata=(
                    json.loads(row["event_metadata"]) if row["event_metadata"] else None
                ),
            )
            for row in rows
        ]

    async def cleanup_old_events(self, before_timestamp: datetime) -> int:
        await self._ensure_initialized()
        assert self._conn is not None

        cursor = await self._conn.execute(
            "DELETE FROM relayer_processed_events WHERE processed_at < ?",
            (before_timestamp.isoformat(),),
        )
        await self._conn.commit()
        return cursor.rowcount

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._initialized = False


class PostgreSQLCheckpointStore(CheckpointStore):
    """PostgreSQL-based checkpoint store for production"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine = create_async_engine(database_url, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Create tables if they don't exist"""
        if self._initialized:
            return

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.event_metadata.create_all)

        self._initialized = True
        logger.info("PostgreSQL checkpoint store initialized")

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        await self._ensure_initialized()

        async with self._session_factory() as session:
            record = CheckpointRecord(
                chain_id=checkpoint.chain_id,
                contract_address=checkpoint.contract_address,
                last_processed_block=checkpoint.last_processed_block,
                last_processed_timestamp=checkpoint.last_processed_timestamp,
                total_events_processed=checkpoint.total_events_processed,
                event_metadata=checkpoint.event_metadata,
            )

            await session.merge(record)
            await session.commit()

            logger.info(
                f"Saved checkpoint: {checkpoint.chain_id}:{checkpoint.contract_address} @ block {checkpoint.last_processed_block}"
            )

    async def get_checkpoint(self, chain_id: str, contract_address: str) -> Optional[Checkpoint]:
        await self._ensure_initialized()

        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointRecord).where(
                    CheckpointRecord.chain_id == chain_id,
                    CheckpointRecord.contract_address == contract_address,
                )
            )
            record = result.scalar_one_or_none()

            if not record:
                return None

            return Checkpoint(
                chain_id=record.chain_id,
                contract_address=record.contract_address,
                last_processed_block=record.last_processed_block,
                last_processed_timestamp=record.last_processed_timestamp,
                total_events_processed=record.total_events_processed,
                event_metadata=record.event_metadata,
            )

    async def mark_event_processed(self, event: ProcessedEvent) -> bool:
        await self._ensure_initialized()

        async with self._session_factory() as session:
            # Check if already processed
            result = await session.execute(
                select(ProcessedEventRecord).where(ProcessedEventRecord.event_id == event.event_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                return False

            record = ProcessedEventRecord(
                event_id=event.event_id,
                chain_id=event.chain_id,
                contract_address=event.contract_address,
                block_number=event.block_number,
                transaction_hash=event.transaction_hash,
                log_index=event.log_index,
                event_name=event.event_name,
                processed_at=event.processed_at,
                published=event.published,
                event_metadata=event.event_metadata,
            )

            session.add(record)
            await session.commit()
            return True

    async def is_event_processed(self, event_id: str) -> bool:
        await self._ensure_initialized()

        async with self._session_factory() as session:
            result = await session.execute(
                select(ProcessedEventRecord).where(ProcessedEventRecord.event_id == event_id)
            )
            return result.scalar_one_or_none() is not None

    async def get_processed_events(
        self, chain_id: str, from_block: int, to_block: int
    ) -> List[ProcessedEvent]:
        await self._ensure_initialized()

        async with self._session_factory() as session:
            result = await session.execute(
                select(ProcessedEventRecord)
                .where(
                    ProcessedEventRecord.chain_id == chain_id,
                    ProcessedEventRecord.block_number >= from_block,
                    ProcessedEventRecord.block_number <= to_block,
                )
                .order_by(ProcessedEventRecord.block_number, ProcessedEventRecord.log_index)
            )

            records = result.scalars().all()
            return [
                ProcessedEvent(
                    event_id=rec.event_id,
                    chain_id=rec.chain_id,
                    contract_address=rec.contract_address,
                    block_number=rec.block_number,
                    transaction_hash=rec.transaction_hash,
                    log_index=rec.log_index,
                    event_name=rec.event_name,
                    processed_at=rec.processed_at,
                    published=rec.published,
                    event_metadata=rec.event_metadata,
                )
                for rec in records
            ]

    async def cleanup_old_events(self, before_timestamp: datetime) -> int:
        await self._ensure_initialized()

        async with self._session_factory() as session:
            result = await session.execute(
                delete(ProcessedEventRecord).where(
                    ProcessedEventRecord.processed_at < before_timestamp
                )
            )
            await session.commit()
            return result.rowcount

    async def close(self) -> None:
        await self._engine.dispose()
