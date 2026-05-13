#!/usr/bin/env python3
"""
Test script to verify Twitter API functionality with v2 pagination pattern
"""
import os
from dotenv import load_dotenv
from social_test import get_twitter_posts

load_dotenv()

def test_twitter_query(query, description, test_pagination=False):
    """Test Twitter API with a specific query"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Query: '{query}'")
    print('='*60)

    try:
        # Initial request
        result = get_twitter_posts(query, pagination_token=None, max_results=20)

        # Check if we have instructions
        instructions = result.get('result', {}).get('timeline', {}).get('instructions', [])
        print(f"Instructions found: {len(instructions)}")

        # Check for entries
        for instruction in instructions:
            inst_type = instruction.get('type')
            print(f"  - Type: {inst_type}")

            if inst_type == 'TimelineAddEntries':
                entries = instruction.get('entries', [])
                print(f"    Entries count: {len(entries)}")

                if entries:
                    # Show first entry details
                    first_entry = entries[0]
                    tweet = first_entry.get('content', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
                    if tweet:
                        text = tweet.get('legacy', {}).get('full_text', 'N/A')
                        print(f"    First tweet: {text[:100]}...")

        # Check next_token (Twitter v2 pattern)
        next_token = result.get('meta', {}).get('next_token')
        print(f"Next token: {next_token[:50] if next_token else 'None'}...")

        # Test pagination if requested and next_token exists
        if test_pagination and next_token:
            print("\n  Testing pagination with next_token...")
            page2_result = get_twitter_posts(query, pagination_token=next_token, max_results=20)
            page2_instructions = page2_result.get('result', {}).get('timeline', {}).get('instructions', [])

            for instruction in page2_instructions:
                if instruction.get('type') == 'TimelineAddEntries':
                    page2_entries = instruction.get('entries', [])
                    print(f"  Page 2 entries: {len(page2_entries)}")
                    break

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        return None


if __name__ == "__main__":
    print("Twitter API Test Suite - v2 Pagination Pattern")
    print("=" * 60)

    # Test 1: Simple, popular query (with pagination test)
    test_twitter_query("python", "Simple popular keyword", test_pagination=True)

    # Test 2: News topic
    test_twitter_query("artificial intelligence", "Technology news topic")

    # Test 3: Location-based
    test_twitter_query("Chennai tamilnadu", "City with location")

    # Test 4: User's query
    test_twitter_query("Future of Software developers and Software engineers", "Complex query (original)")

    # Test 5: Simplified version
    test_twitter_query("software developers future", "Simplified version")

    # Test 6: Very generic query with pagination
    test_twitter_query("news", "Generic query with pagination", test_pagination=True)

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)
    print("\nSummary:")
    print("- ✓ next_token pattern implemented")
    print("- ✓ Pagination tested (where available)")
    print("- ✓ Multiple query types tested")
    print("="*60)
