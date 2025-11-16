#!/usr/bin/env python3
"""Trigger processing of raw_data to posts_table"""
import asyncio
from app.services.pipeline_orchestrator import PipelineOrchestrator

async def main():
    print("Starting raw data processing...")
    orchestrator = PipelineOrchestrator()

    # Process pending raw data (convert to posts_table)
    result = await orchestrator.process_pending_raw_data(limit=100)

    print(f"\n✓ Processing complete:")
    print(f"  - Processed: {result.get('processed', 0)}")
    print(f"  - Saved to posts_table: {result.get('saved', 0)}")
    print(f"  - Errors: {result.get('errors_count', 0)}")

    if result.get('errors'):
        print(f"\nErrors encountered:")
        for error in result.get('errors', [])[:5]:
            print(f"  - {error}")

if __name__ == '__main__':
    asyncio.run(main())
