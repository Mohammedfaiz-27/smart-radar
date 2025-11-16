#!/usr/bin/env python3
"""Check cluster platform configurations"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json

async def main():
    connection_string = "mongodb+srv://dbusr:dbusr123@smart-radar.tbapili.mongodb.net/smart_radar?retryWrites=true&w=majority&appName=smart-radar"
    client = AsyncIOMotorClient(connection_string)
    db = client.smart_radar

    clusters = await db.clusters.find({}).to_list(length=100)

    print(f"Found {len(clusters)} clusters\n")

    for cluster in clusters:
        print(f"Cluster: {cluster.get('name')}")
        print(f"  Type: {cluster.get('cluster_type')}")
        print(f"  Active: {cluster.get('is_active')}")

        platform_config = cluster.get('platform_config', {})
        if platform_config:
            print(f"  Platform Config:")
            for platform, config in platform_config.items():
                enabled = config.get('enabled', False)
                print(f"    {platform}: {'✓ Enabled' if enabled else '✗ Disabled'}")
        else:
            print(f"  Platform Config: None (will use defaults)")
        print()

    client.close()

if __name__ == '__main__':
    asyncio.run(main())
