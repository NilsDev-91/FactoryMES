import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select, delete, Session
from sqlalchemy.orm import selectinload
from rich.console import Console
from rich.table import Table
from rich.live import Live

from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum
from app.models.order import Order, OrderItem

console = Console()

async def cleanup_orders():
    """Wipe the slate clean for a fresh logic test."""
    async with async_session_maker() as session:
        print("🧹 Cleaning up old Orders and Jobs...")
        await session.exec(delete(Job))
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        await session.commit()

async def inject_order(ebay_id: str, sku: str):
    """Simulate an external eBay webhook injecting a raw order into the DB."""
    async with async_session_maker() as session:
        print(f"📦 [External] New Order received: {ebay_id} ({sku}). Waiting for FactoryOS Brain...")
        
        # 1. Create Order
        db_order = Order(
            ebay_order_id=ebay_id,
            buyer_username="SimulatedBuyer",
            total_price=29.99,
            currency="USD",
            status="PENDING",
            created_at=datetime.now(timezone.utc)
        )
        session.add(db_order)
        await session.flush()
        
        # 2. Create OrderItem (The trigger for the Brain)
        db_item = OrderItem(
            order_id=db_order.id,
            sku=sku,
            title=f"Sample {sku}",
            quantity=1
        )
        session.add(db_item)
        await session.commit()

def generate_job_table(jobs: list) -> Table:
    table = Table(title="FactoryOS Brain - Passive Monitoring")
    table.add_column("Order ID", justify="left", style="cyan")
    table.add_column("Job ID", justify="center", style="magenta")
    table.add_column("SKU", justify="left", style="green")
    table.add_column("Status", justify="left")
    table.add_column("Printer", justify="left", style="yellow")
    table.add_column("Requirements", justify="left", style="blue")

    for job in jobs:
        order_id = job.order.ebay_order_id if job.order else "N/A"
        sku = job.order.items[0].sku if job.order and job.order.items else "N/A"
        reqs = str(job.filament_requirements)
        
        status_color = "white"
        if job.status == JobStatusEnum.PENDING: status_color = "yellow"
        elif job.status == JobStatusEnum.PRINTING: status_color = "green"
        elif job.status == JobStatusEnum.FAILED: status_color = "red"
        
        table.add_row(
            order_id,
            str(job.id),
            sku,
            f"[{status_color}]{job.status}[/{status_color}]",
            job.assigned_printer_serial or "WAITTING...",
            reqs
        )
    return table

async def monitor_jobs():
    """Passive monitoring loop to watch the Brain's decisions."""
    with Live(auto_refresh=False) as live:
        while True:
            async with async_session_maker() as session:
                stmt = select(Job).options(
                    selectinload(Job.order).selectinload(Order.items)
                )
                jobs = (await session.exec(stmt)).all()
                live.update(generate_job_table(jobs), refresh=True)
            await asyncio.sleep(2)

async def main():
    console.print("[bold cyan]FACTORY-OS AUTONOMOUS LOGIC TEST[/bold cyan]")
    
    # 1. Cleanup
    await cleanup_orders()
    
    # Start Monitoring in background
    monitor_task = asyncio.create_task(monitor_jobs())
    
    # 2. Injection 1
    await inject_order("AUTO-TEST-1", "KEGEL-V3-BLACK")
    
    # 3. Wait 10s
    console.print("[dim]Waiting 10s for Injection 2...[/dim]")
    await asyncio.sleep(10)
    
    # 4. Injection 2
    await inject_order("AUTO-TEST-2", "ZYLINDER-V2-RED")
    
    # Let it run indefinitely or until manually stopped
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Simulation stopped by user.")
