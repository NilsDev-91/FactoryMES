import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.core import Printer, PrinterStatusEnum
from app.schemas.printer_cache import PrinterStateCache
from app.models.printer import PrinterRead
from app.core.redis import get_redis_client

class PrinterService:
    def _merge_state(self, printer_db: Printer, cached_state: Optional[PrinterStateCache]) -> PrinterRead:
        """
        Merges DB configuration with real-time cached telemetry.
        """
        # Convert DB object to dict for base model initialization
        printer_data = printer_db.model_dump()
        
        if cached_state:
            # Overwrite with hot telemetry
            printer_data["status"] = cached_state.status
            printer_data["temps"] = cached_state.temps
            printer_data["nozzle_temp"] = cached_state.temps.get("nozzle", 0.0)
            printer_data["bed_temp"] = cached_state.temps.get("bed", 0.0)
            printer_data["progress"] = cached_state.progress
            printer_data["remaining_time_min"] = cached_state.remaining_time_min
            printer_data["active_file"] = cached_state.active_file
            printer_data["ams"] = cached_state.ams
            printer_data["is_online"] = not cached_state.is_stale
        else:
            # OFFLINE Fallback
            printer_data["status"] = PrinterStatusEnum.OFFLINE
            printer_data["temps"] = {"nozzle": 0.0, "bed": 0.0}
            printer_data["nozzle_temp"] = 0.0
            printer_data["bed_temp"] = 0.0
            printer_data["progress"] = 0
            printer_data["remaining_time_min"] = 0
            printer_data["active_file"] = None
            printer_data["is_online"] = False
            printer_data["ams"] = []

        return PrinterRead(**printer_data)

    async def get_printer(self, session: AsyncSession, serial: str) -> Optional[PrinterRead]:
        """
        Fetch single printer with merged state.
        """
        # 1. DB Fetch
        statement = select(Printer).where(Printer.serial == serial).options(selectinload(Printer.ams_slots))
        result = await session.execute(statement)
        printer_db = result.scalars().first()
        if not printer_db:
            return None

        # 2. Redis Fetch
        redis = get_redis_client()
        key = f"printer:{serial}:status"
        raw_state = await redis.get(key)
        
        cached_state = None
        if raw_state:
            cached_state = PrinterStateCache.model_validate_json(raw_state)

        return self._merge_state(printer_db, cached_state)

    async def get_printers(self, session: AsyncSession) -> List[PrinterRead]:
        """
        Fetch all printers with merged state (Optimized via MGET).
        """
        # 1. Fetch all static config from DB
        statement = select(Printer).options(selectinload(Printer.ams_slots))
        result = await session.execute(statement)
        printers_db = result.scalars().all()
        
        if not printers_db:
            return []

        # 2. Batch fetch all hot states from Redis (MGET)
        redis = get_redis_client()
        keys = [f"printer:{p.serial}:status" for p in printers_db]
        raw_states = await redis.mget(keys)
        
        # 3. Zip and Merge
        merged_results = []
        for printer_db, raw_state in zip(printers_db, raw_states):
            cached_state = None
            if raw_state:
                cached_state = PrinterStateCache.model_validate_json(raw_state)
            
            merged_results.append(self._merge_state(printer_db, cached_state))
            
        return merged_results
