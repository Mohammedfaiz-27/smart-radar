#!/usr/bin/env python3
import asyncio
from app.core.database import connect_to_mongo, get_database

async def check_platforms():
    await connect_to_mongo()
    db = get_database()
    collection = db.social_posts
    
    # Get platform distribution for 'own' cluster type
    pipeline = [
        {'$match': {'cluster_type': 'own'}},
        {'$group': {
            '_id': '$platform',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}}
    ]
    
    results = []
    async for doc in collection.aggregate(pipeline):
        results.append(doc)
    
    print('Platform breakdown for Own Organization:')
    total = 0
    for result in results:
        platform = result['_id']
        count = result['count']
        total += count
        print(f'  {platform}: {count} posts')
    print(f'Total: {total} posts')

if __name__ == "__main__":
    asyncio.run(check_platforms())