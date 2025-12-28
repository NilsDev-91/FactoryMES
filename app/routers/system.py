import os
import logging
from fastapi import APIRouter, HTTPException
from dotenv import set_key

from app.models.system import EbayConfigUpdate
import app.core.config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System Management"])

@router.post("/config/ebay")
async def update_ebay_config(config: EbayConfigUpdate):
    """
    Updates the eBay configuration in the .env file and reloads it in memory.
    
    WARNING: This endpoint handles sensitive credentials. 
    In production, it must be protected by authentication and authorization.
    """
    env_path = ".env"
    
    try:
        # 1. Update .env file
        set_key(env_path, "EBAY_APP_ID", config.ebay_app_id)
        set_key(env_path, "EBAY_CERT_ID", config.ebay_cert_id)
        set_key(env_path, "EBAY_RU_NAME", config.ebay_ru_name)
        set_key(env_path, "EBAY_API_ENV", config.ebay_env)
        
        # 2. Update os.environ for immediate effect in tools reading env directly
        os.environ["EBAY_APP_ID"] = config.ebay_app_id
        os.environ["EBAY_CERT_ID"] = config.ebay_cert_id
        os.environ["EBAY_RU_NAME"] = config.ebay_ru_name
        os.environ["EBAY_API_ENV"] = config.ebay_env
        
        # 3. Force reload of the global settings object
        # This creates a new instance of Settings which re-reads the environment
        app.core.config.settings = app.core.config.Settings()
        
        logger.info("eBay configuration updated and reloaded successfully.")
        
        return {
            "status": "success",
            "message": "eBay configuration saved and reloaded in memory.",
            "current_env": app.core.config.settings.EBAY_API_ENV
        }
        
    except Exception as e:
        logger.error(f"Failed to update eBay configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.get("/config/status")
async def get_config_status():
    """
    Returns the status of the eBay configuration (whether keys are set).
    """
    settings = app.core.config.settings
    # Check if required keys are set and not placeholders
    is_configured = all([
        settings.EBAY_APP_ID and settings.EBAY_APP_ID != "your_ebay_app_id",
        settings.EBAY_CERT_ID and settings.EBAY_CERT_ID != "your_ebay_cert_id",
        settings.EBAY_RU_NAME and settings.EBAY_RU_NAME != "your_ebay_ru_name"
    ])
    
    return {
        "ebay_configured": is_configured,
        "environment": settings.EBAY_API_ENV,
        # Provide masked values for preview if needed
        "config_preview": {
            "ebay_app_id": f"{settings.EBAY_APP_ID[:4]}...{settings.EBAY_APP_ID[-4:]}" if settings.EBAY_APP_ID else None,
            "ebay_env": settings.EBAY_API_ENV
        }
    }
