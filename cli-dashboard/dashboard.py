#!/usr/bin/env python3
"""
Ashiorid AI Manager - CLI Dashboard

Real-time monitoring dashboard for all services.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# Service endpoints
SERVICES = {
    "llm-proxy": "http://localhost:8001",
    "lore-rag": "http://localhost:8002",
    "character-agent": "http://localhost:8003",
    "simulation-engine": "http://localhost:8004",
    "ai-manager": "http://localhost:8005",
}

# Kubernetes mode (if running in cluster)
K8S_MODE = False
K8S_NAMESPACE = "ashiorid"


class ServiceMonitor:
    """Monitor for Ashiorid services."""

    def __init__(self):
        self.console = Console()
        self.client = httpx.AsyncClient(timeout=5.0)
        self.service_stats: Dict[str, Dict] = {}
        self.last_update = time.time()

    async def check_service_health(self, service_name: str, url: str) -> Dict:
        """Check health of a single service."""
        try:
            response = await self.client.get(f"{url}/health")
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "version": data.get("version", "unknown"),
                    "response_time": response.elapsed.total_seconds() * 1000,
                }
        except httpx.ConnectError:
            return {"status": "offline", "version": "n/a", "response_time": 0}
        except Exception as e:
            return {"status": "error", "version": "n/a", "response_time": 0, "error": str(e)}

        return {"status": "unhealthy", "version": "n/a", "response_time": 0}

    async def get_service_stats(self, service_name: str, url: str) -> Optional[Dict]:
        """Get detailed stats for a service."""
        try:
            response = await self.client.get(f"{url}/stats", timeout=3.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def get_llm_proxy_stats(self) -> Optional[Dict]:
        """Get LLM proxy specific stats."""
        try:
            url = SERVICES.get("llm-proxy")
            if not url:
                return None

            # Get general stats
            stats_response = await self.client.get(f"{url}/stats", timeout=3.0)
            cost_response = await self.client.get(f"{url}/cost/summary", timeout=3.0)

            if stats_response.status_code == 200 and cost_response.status_code == 200:
                return {
                    "stats": stats_response.json(),
                    "cost": cost_response.json(),
                }
        except Exception:
            pass
        return None

    def create_header(self) -> Panel:
        """Create header panel."""
        header_text = Text()
        header_text.append("🌍 Ashiorid AI Manager", style="bold cyan")
        header_text.append(" - Real-time Dashboard\n", style="bold white")
        header_text.append(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

        return Panel(header_text, style="cyan", border_style="bright_cyan")

    def create_services_table(self) -> Table:
        """Create services status table."""
        table = Table(title="Service Status", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan", width=20)
        table.add_column("Status", width=12)
        table.add_column("Version", width=10)
        table.add_column("Response Time", justify="right", width=15)

        for service_name, stats in self.service_stats.items():
            status = stats.get("status", "unknown")

            # Color code status
            if status == "healthy":
                status_text = Text("✓ Healthy", style="green")
            elif status == "offline":
                status_text = Text("✗ Offline", style="red")
            elif status == "error":
                status_text = Text("⚠ Error", style="yellow")
            else:
                status_text = Text("? Unknown", style="dim")

            version = stats.get("version", "n/a")
            response_time = stats.get("response_time", 0)
            response_str = f"{response_time:.1f}ms" if response_time > 0 else "n/a"

            table.add_row(
                service_name,
                status_text,
                version,
                response_str,
            )

        return table

    def create_llm_proxy_panel(self, llm_stats: Optional[Dict]) -> Panel:
        """Create LLM proxy statistics panel."""
        if not llm_stats:
            return Panel("LLM Proxy: No data available", title="LLM Proxy", style="yellow")

        stats = llm_stats.get("stats", {})
        cost = llm_stats.get("cost", {})

        # Create stats table
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        # Request stats
        total_requests = stats.get("total_requests", 0)
        successful = stats.get("successful_requests", 0)
        failed = stats.get("failed_requests", 0)
        success_rate = (successful / max(total_requests, 1)) * 100

        table.add_row("Total Requests", str(total_requests))
        table.add_row("Success Rate", f"{success_rate:.1f}%")
        table.add_row("Failed Requests", str(failed))

        # Cache stats
        cache_stats = stats.get("cache_stats", {})
        if cache_stats.get("enabled"):
            hit_rate = cache_stats.get("hit_rate", 0) * 100
            table.add_row("Cache Hit Rate", f"{hit_rate:.1f}%")

        # Cost stats
        total_cost = cost.get("total_cost_usd", 0)
        table.add_row("Total Cost", f"${total_cost:.4f}")

        return Panel(table, title="LLM Proxy Stats", style="green")

    def create_layout(self) -> Layout:
        """Create dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main", ratio=1),
        )

        layout["main"].split_row(
            Layout(name="services"),
            Layout(name="details"),
        )

        return layout

    async def update_stats(self):
        """Update service statistics."""
        # Check all services
        tasks = []
        for service_name, url in SERVICES.items():
            tasks.append(self.check_service_health(service_name, url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update service stats
        for service_name, result in zip(SERVICES.keys(), results):
            if isinstance(result, dict):
                self.service_stats[service_name] = result

        self.last_update = time.time()

    async def run(self):
        """Run the dashboard."""
        layout = self.create_layout()

        with Live(layout, refresh_per_second=1, screen=True):
            while True:
                # Update stats
                await self.update_stats()

                # Get LLM proxy specific stats
                llm_stats = await self.get_llm_proxy_stats()

                # Update layout
                layout["header"].update(self.create_header())
                layout["services"].update(Panel(self.create_services_table(), border_style="cyan"))
                layout["details"].update(self.create_llm_proxy_panel(llm_stats))

                # Wait before next update
                await asyncio.sleep(2)

    async def cleanup(self):
        """Cleanup resources."""
        await self.client.aclose()


async def main():
    """Main entry point."""
    console = Console()

    console.print("\n[bold cyan]Starting Ashiorid AI Manager Dashboard...[/bold cyan]\n")

    monitor = ServiceMonitor()

    try:
        await monitor.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped by user[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
    finally:
        await monitor.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
