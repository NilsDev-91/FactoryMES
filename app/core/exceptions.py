from fastapi import HTTPException, status

class FactoryOSException(HTTPException):
    """Base exception for FactoryOS Logic Errors."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class PrinterBusyError(FactoryOSException):
    """
    Raised when an action is requested but the printer is in a blocking state 
    (e.g., PRINTING, CLEARING_BED) and force was not specified.
    """
    def __init__(self, printer_serial: str, current_state: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Printer {printer_serial} is currently {current_state}. Retry logic or manual override required."
        )

class FilamentMismatchError(FactoryOSException):
    """
    Raised when the requested material requirements cannot be met by the 
    current AMS configuration of the printer.
    """
    def __init__(self, printer_serial: str, required_color: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Printer {printer_serial} cannot fulfill requirement for color {required_color}. No matching AMS slot found."
        )

class ResourceNotFoundError(FactoryOSException):
    """Strict 404 for when a specific business entity is missing."""
    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} with ID {identifier} not found."
        )

class SafetyException(Exception):
    """
    Raised when a physical safety constraint is violated.
    NOT an HTTP exception - this is for internal logic guards.
    Example: Attempting Smart Gantry Sweep on parts below minimum safe height.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
