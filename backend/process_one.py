#!/usr/bin/env python3
"""Process one raw_data entry to test the pipeline"""
import asyncio
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.raw_data_service import RawDataService

async def main():
    print("Processing ONE raw_data entry for testing...")

    # Get one pending entry
    raw_service = RawDataService()
    pending = await raw_service.get_pending_entries(limit=1)

    if not pending:
        print("No pending entries found")
        return

    print(f"Found 1 pending entry: {pending[0].id}")
    print(f"Platform: {pending[0].platform}")
    print(f"Keyword: {pending[0].keyword}")
    print(f"Has raw_json: {bool(pending[0].raw_json)}")

    # Process it
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.process_pending_raw_data(limit=1)

    print(f"\n✓ Result:")
    print(f"  Processed: {result.get('processed', 0)}")
    print(f"  Saved: {result.get('saved', 0)}")
    print(f"  Errors: {result.get('errors_count', 0)}")

    if result.get('errors'):
        print(f"\nErrors:")
        for error in result.get('errors', []):
            print(f"  - {error}")

if __name__ == '__main__':
    asyncio.run(main())
