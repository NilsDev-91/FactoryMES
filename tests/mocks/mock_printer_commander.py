"""
MockPrinterCommander - Simulation-safe printer command interface.

This mock replaces the real PrinterCommander for testing scenarios,
avoiding actual FTPS uploads and MQTT commands while still exercising
the full business logic stack.
"""
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger("MockPrinterCommander")

class MockPrinterCommander:
    """
    A simulation-safe replacement for PrinterCommander.
    Logs all operations but performs no actual hardware communication.
    """
    
    def __init__(self):
        self.upload_log: List[dict] = []
        self.start_log: List[dict] = []
        self.maintenance_log: List[dict] = []
    
    async def start_job(
        self,
        printer,
        job,
        ams_mapping: List[int],
        is_calibration_due: bool = True
    ) -> None:
        """
        Mock implementation of job start.
        Logs the event and returns success without hardware interaction.
        """
        event = {
            "printer_serial": printer.serial,
            "job_id": job.id,
            "job_gcode_path": job.gcode_path,
            "ams_mapping": ams_mapping,
            "is_calibration_due": is_calibration_due
        }
        self.start_log.append(event)
        
        cal_status = "FULL CALIBRATION" if is_calibration_due else "OPTIMIZED (Calibration Skipped)"
        logger.info(
            f"[MOCK] start_job -> Printer: {printer.serial}, "
            f"Job: {job.id}, "
            f"AMS Mapping: {ams_mapping[:4]}..., "
            f"Mode: {cal_status}"
        )
    
    async def start_maintenance_job(self, printer, file_path: Path) -> None:
        """
        Mock implementation of maintenance job (e.g., bed clearing).
        """
        event = {
            "printer_serial": printer.serial,
            "maintenance_file": str(file_path)
        }
        self.maintenance_log.append(event)
        
        logger.info(
            f"[MOCK] start_maintenance_job -> Printer: {printer.serial}, "
            f"File: {file_path.name if hasattr(file_path, 'name') else file_path}"
        )
    
    async def upload_file(self, printer, local_path: Path, remote_path: str) -> bool:
        """
        Mock implementation of FTPS file upload.
        Returns success without actual upload.
        """
        event = {
            "printer_serial": printer.serial,
            "local_path": str(local_path),
            "remote_path": remote_path
        }
        self.upload_log.append(event)
        
        logger.info(
            f"[MOCK] upload_file -> Printer: {printer.serial}, "
            f"Local: {local_path}, Remote: {remote_path}"
        )
        return True
    
    def get_summary(self) -> dict:
        """
        Returns a summary of all mock operations performed.
        Useful for test assertions and debugging.
        """
        return {
            "total_uploads": len(self.upload_log),
            "total_starts": len(self.start_log),
            "total_maintenance": len(self.maintenance_log),
            "uploads": self.upload_log,
            "starts": self.start_log,
            "maintenance": self.maintenance_log
        }
