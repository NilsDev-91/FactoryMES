import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.core import Printer, PrinterStatusEnum, JobStatusEnum, PrinterTypeEnum, Job, ClearingStrategyEnum
from app.services.printer.mqtt_worker import PrinterMqttWorker

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class TestThermalWatchdogLoopClosure(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(DATABASE_URL)
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        self.async_session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        
        # Patch async_session_maker to return a NEW session each time (mimic real behavior)
        self.session_patcher = patch("app.services.printer.mqtt_worker.async_session_maker", side_effect=self.async_session_factory)
        self.session_patcher.start()
        
        # Mock JobDispatcher.dispatch_next_job to be a coroutine
        self.dispatcher_patcher = patch("app.services.printer.mqtt_worker.job_dispatcher.dispatch_next_job", new_callable=AsyncMock)
        self.mock_dispatch = self.dispatcher_patcher.start()
        
        # Mock PrintJobExecutionService to avoid its handle_print_finished logic
        self.executor_patcher = patch("app.services.printer.mqtt_worker.PrintJobExecutionService")
        self.mock_executor_class = self.executor_patcher.start()
        self.mock_executor = AsyncMock()
        self.mock_executor_class.return_value = self.mock_executor
        
        self.worker = PrinterMqttWorker()

    async def asyncTearDown(self):
        self.session_patcher.stop()
        self.dispatcher_patcher.stop()
        self.executor_patcher.stop()
        await self.engine.dispose()

    async def test_thermal_watchdog_trigger(self):
        """Verify Thermal Watchdog triggers clearing when bed temp drops below threshold."""
        print("\n[RUNNING] Thermal Watchdog Trigger Test")
        
        async with self.async_session_factory() as session:
            printer = Printer(
                serial="SN_THERMAL",
                name="Thermal Printer",
                type=PrinterTypeEnum.A1,
                current_status=PrinterStatusEnum.COOLDOWN,
                thermal_release_temp=30.0,
                current_temp_bed=50.0,
                can_auto_eject=True,
                clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING
            )
            session.add(printer)
            await session.commit()
        
        # Mock _trigger_ejection
        self.worker._trigger_ejection = AsyncMock()
        
        # Inject telemetry where bed_temper <= threshold
        telemetry = {"print": {"bed_temper": 28.0, "gcode_state": "FINISH"}}
        await self.worker._handle_message("SN_THERMAL", telemetry)
        
        self.worker._trigger_ejection.assert_called_once_with("SN_THERMAL")
        print("[PASS] Thermal Watchdog Triggered")

    async def test_loop_closure_finish_event(self):
        """Verify loop closure when CLEARING_BED finishes."""
        print("\n[RUNNING] Loop Closure Finish Event Test")
        
        async with self.async_session_factory() as session:
            printer = Printer(
                serial="SN_LOOP",
                name="Loop Printer",
                type=PrinterTypeEnum.A1,
                current_status=PrinterStatusEnum.CLEARING_BED,
                is_plate_cleared=False,
                can_auto_eject=True,
                clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING
            )
            session.add(printer)
            await session.commit()
        
        # Inject FINISH event
        message = {"print": {"gcode_state": "FINISH"}}
        await self.worker._handle_message("SN_LOOP", message)
        
        # Reload printer to verify state
        async with self.async_session_factory() as session:
            printer = await session.get(Printer, "SN_LOOP")
            self.assertEqual(printer.current_status, PrinterStatusEnum.IDLE)
            self.assertTrue(printer.is_plate_cleared)
        
        # Verify JobDispatcher was triggered immediately
        # Wait a bit for the background task to start/run
        await asyncio.sleep(0.2)
        # Note: We can't easily assert on the session instance because it's local to the _handle_message call
        self.mock_dispatch.assert_called_once()
        print("[PASS] Loop Closure Success")

if __name__ == "__main__":
    unittest.main()
