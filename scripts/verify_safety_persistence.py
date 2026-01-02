import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.core import Job, Printer, JobStatusEnum, PrinterStatusEnum, ClearingStrategyEnum, PrinterTypeEnum
from app.services.print_job_executor import PrintJobExecutionService

# In-memory SQLite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class TestSafetyPersistence(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Setup in-memory database
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Mocks
        self.mock_filament_manager = MagicMock()
        self.mock_printer_commander = AsyncMock()
        self.mock_bed_clearing_service = MagicMock()
        
        self.session = self.async_session()
        self.executor = PrintJobExecutionService(
            session=self.session,
            filament_manager=self.mock_filament_manager,
            printer_commander=self.mock_printer_commander,
            bed_clearing_service=self.mock_bed_clearing_service
        )

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()

    async def setup_test_data(self, can_auto_eject: bool, job_metadata: dict = None):
        printer = Printer(
            serial="TEST_PRINTER",
            name="Test Printer",
            type=PrinterTypeEnum.A1,
            can_auto_eject=can_auto_eject,
            clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING,
            current_status=PrinterStatusEnum.PRINTING
        )
        
        job = Job(
            id=1,
            order_id=101,
            assigned_printer_serial="TEST_PRINTER",
            gcode_path="dummy.gcode",
            status=JobStatusEnum.PRINTING,
            job_metadata=job_metadata or {}
        )
        
        printer.current_job_id = job.id
        
        self.session.add(printer)
        self.session.add(job)
        await self.session.commit()
        return printer, job

    async def test_scenario_a_short_part_unsafe(self):
        """Scenario A: 'The Short Part' (Unsafe) - Should transition to AWAITING_CLEARANCE"""
        print("\n[RUNNING] Scenario A: The Short Part (Unsafe)")
        
        metadata = {"is_auto_eject_enabled": False, "detected_height": 20.0}
        await self.setup_test_data(can_auto_eject=True, job_metadata=metadata)
        
        await self.executor.handle_print_finished("TEST_PRINTER", job_id=1)
        
        # Reload printer
        printer = await self.session.get(Printer, "TEST_PRINTER")
        print(f"Resulting Status: {printer.current_status}")
        
        self.assertEqual(printer.current_status, PrinterStatusEnum.AWAITING_CLEARANCE)
        print("[PASS] Scenario A")

    async def test_scenario_b_tall_part_safe(self):
        """Scenario B: 'The Tall Part' (Safe) - Should transition to COOLDOWN"""
        print("\n[RUNNING] Scenario B: The Tall Part (Safe)")
        
        metadata = {"is_auto_eject_enabled": True, "detected_height": 55.0}
        await self.setup_test_data(can_auto_eject=True, job_metadata=metadata)
        
        await self.executor.handle_print_finished("TEST_PRINTER", job_id=1)
        
        # Reload printer
        printer = await self.session.get(Printer, "TEST_PRINTER")
        print(f"Resulting Status: {printer.current_status}")
        
        self.assertEqual(printer.current_status, PrinterStatusEnum.COOLDOWN)
        print("[PASS] Scenario B")

    async def test_scenario_c_legacy_fallback(self):
        """Scenario C: 'Legacy/Unknown Job' (Fallback) - Should transition to AWAITING_CLEARANCE"""
        print("\n[RUNNING] Scenario C: Legacy/Unknown Job (Fallback)")
        
        # Metadata is None or empty
        await self.setup_test_data(can_auto_eject=True, job_metadata=None)
        
        await self.executor.handle_print_finished("TEST_PRINTER", job_id=1)
        
        # Reload printer
        printer = await self.session.get(Printer, "TEST_PRINTER")
        print(f"Resulting Status: {printer.current_status}")
        
        self.assertEqual(printer.current_status, PrinterStatusEnum.AWAITING_CLEARANCE)
        print("[PASS] Scenario C")

if __name__ == "__main__":
    unittest.main()
