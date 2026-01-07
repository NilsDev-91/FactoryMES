import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.models.core import Printer, Job, JobStatusEnum
from app.services.logic.color_matcher import color_matcher
from sqlmodel import select
from sqlalchemy.orm import selectinload

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("debug")

async def debug_match():
    logger.info("DEBUG: Debugging Filament Matching...")
    async with async_session_maker() as session:
        # Load Printer
        stmt = select(Printer).options(selectinload(Printer.ams_slots))
        printer = (await session.exec(stmt)).first()
        if not printer:
            logger.info("ERROR: No printer found.")
            return
            
        logger.info(f"Printer: {printer.name} ({printer.serial})")
        for s in printer.ams_slots:
            logger.info(f"   [Slot {s.slot_id}] {s.material} | {s.color_hex} | {s.color_name}")

        # Load Jobs
        stmt = select(Job).where(Job.status == JobStatusEnum.PENDING)
        jobs = (await session.exec(stmt)).all()
        
        for j in jobs:
            logger.info(f"Job {j.id}: {j.filament_requirements}")
            if not j.filament_requirements: continue
            
            req = j.filament_requirements[0]
            req_mat = req.get("material")
            req_col = req.get("hex_color") or req.get("color")
            
            logger.info(f"   Target: {req_mat} | {req_col}")
            
            matched = False
            for s in printer.ams_slots:
                mat_match = s.material and s.material.upper() == req_mat.upper()
                col_match = color_matcher.is_color_match(req_col, s.color_hex)
                logger.info(f"      - Slot {s.slot_id}: MatMatch={mat_match}, ColMatch={col_match}")
                if mat_match and col_match:
                    logger.info(f"      SUCCESS: MATCH FOUND!")
                    matched = True
            
            if not matched:
                logger.info(f"      FAILURE: NO MATCH for Job {j.id}")

if __name__ == "__main__":
    asyncio.run(debug_match())
