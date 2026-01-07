import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select, delete
from app.models.core import Product, Printer, PrinterStatusEnum, ProductRequirement
from app.models.product_sku import ProductSKU
from app.models.filament import FilamentProfile, AmsSlot

async def setup_smart_data():
    async with async_session_maker() as session:
        # 1. Filament Profiles
        print("🧵 Creating Filament Profiles...")
        black_pla_stmt = select(FilamentProfile).where(FilamentProfile.color_hex == "#000000", FilamentProfile.material == "PLA")
        black_pla = (await session.exec(black_pla_stmt)).first()
        if not black_pla:
            black_pla = FilamentProfile(brand="Generic", material="PLA", color_hex="#000000", color_name="Black", density=1.24, spool_weight=1000)
            session.add(black_pla)
        else:
            black_pla.color_name = "Black"
            session.add(black_pla)
            
        red_pla_stmt = select(FilamentProfile).where(FilamentProfile.color_hex == "#FF0000", FilamentProfile.material == "PLA")
        red_pla = (await session.exec(red_pla_stmt)).first()
        if not red_pla:
            red_pla = FilamentProfile(brand="Generic", material="PLA", color_hex="#FF0000", color_name="Red", density=1.24, spool_weight=1000)
            session.add(red_pla)
        else:
            red_pla.color_name = "Red"
            session.add(red_pla)
        
        await session.flush()
        
        # 2. Products & SKUs
        print("📦 Setting up Products and SKUs...")
        
        # Kegel V3
        kegel_master_stmt = select(Product).where(Product.sku == "KEGEL-V3-MASTER")
        kegel_master = (await session.exec(kegel_master_stmt)).first()
        if not kegel_master:
            kegel_master = Product(name="Kegel V3", sku="KEGEL-V3-MASTER", print_file_id=18, part_height_mm=45.0, is_continuous_printing=True)
            session.add(kegel_master)
        await session.flush()
        
        kegel_black_stmt = select(ProductSKU).where(ProductSKU.sku == "KEGEL-V3-BLACK")
        kegel_black = (await session.exec(kegel_black_stmt)).first()
        if not kegel_black:
            kegel_black = ProductSKU(sku="KEGEL-V3-BLACK", name="Kegel V3 Black", product_id=kegel_master.id, hex_color="#000000")
            session.add(kegel_black)
        await session.flush()
        
        # Req for Kegel Black
        kegel_req_stmt = select(ProductRequirement).where(ProductRequirement.product_sku_id == kegel_black.id)
        if not (await session.exec(kegel_req_stmt)).first():
            kegel_req = ProductRequirement(product_sku_id=kegel_black.id, filament_profile_id=black_pla.id)
            session.add(kegel_req)

        # Zylinder V2
        zyl_master_stmt = select(Product).where(Product.sku == "ZYLINDER-V2-MASTER")
        zyl_master = (await session.exec(zyl_master_stmt)).first()
        if not zyl_master:
            zyl_master = Product(name="Zylinder V2", sku="ZYLINDER-V2-MASTER", print_file_id=16, part_height_mm=52.0, is_continuous_printing=True)
            session.add(zyl_master)
        await session.flush()
        
        zyl_red_stmt = select(ProductSKU).where(ProductSKU.sku == "ZYLINDER-V2-RED")
        zyl_red = (await session.exec(zyl_red_stmt)).first()
        if not zyl_red:
            zyl_red = ProductSKU(sku="ZYLINDER-V2-RED", name="Zylinder V2 Red", product_id=zyl_master.id, hex_color="#FF0000")
            session.add(zyl_red)
        await session.flush()
        
        # Req for Zylinder Red
        zyl_req_stmt = select(ProductRequirement).where(ProductRequirement.product_sku_id == zyl_red.id)
        if not (await session.exec(zyl_req_stmt)).first():
            zyl_req = ProductRequirement(product_sku_id=zyl_red.id, filament_profile_id=red_pla.id)
            session.add(zyl_req)

        # 3. Printer AMS Setup
        print("📠 Configuring AMS for A1 REAL...")
        REAL_SERIAL = "03919C461802608"
        await session.exec(delete(AmsSlot).where(AmsSlot.printer_id == REAL_SERIAL))
        
        # Slot 1: Black
        session.add(AmsSlot(printer_id=REAL_SERIAL, ams_index=0, slot_index=0, slot_id=0, color_hex="#000000FF", material="PLA"))
        # Slot 2: Red
        session.add(AmsSlot(printer_id=REAL_SERIAL, ams_index=0, slot_index=1, slot_id=1, color_hex="#FF0000FF", material="PLA"))
        
        await session.commit()
    print("✅ Smart Data seeded successfully.")

if __name__ == "__main__":
    asyncio.run(setup_smart_data())
