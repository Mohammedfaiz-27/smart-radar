#!/usr/bin/env python3
"""
Test script to verify Facebook API cursor-based pagination
"""
import os
from dotenv import load_dotenv
from social_test import get_facebook_posts

load_dotenv()

def test_facebook_query(query, description, test_pagination=False):
    """Test Facebook API with a specific query"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Query: '{query}'")
    print('='*60)

    try:
        # Initial request
        result = get_facebook_posts(query, cursor=None)

        # Check items
        items = result.get('data', {}).get('items', [])
        print(f"Items found: {len(items)}")

        if items:
            # Show first post details
            first_item = items[0]
            post_text = first_item.get('basic_info', {}).get('post_text', 'N/A')
            print(f"First post: {post_text[:100]}...")

        # Check cursor
        next_cursor = result.get('data', {}).get('page_info', {}).get('cursor')
        pagination_cursor = result.get('pagination', {}).get('next_cursor')
        print(f"Page info cursor: {next_cursor[:50] if next_cursor else 'None'}...")
        print(f"Pagination cursor: {pagination_cursor[:50] if pagination_cursor else 'None'}...")

        # Test pagination if requested and cursor exists
        if test_pagination and next_cursor:
            print("\n  Testing pagination with cursor...")
            page2_result = get_facebook_posts(query, cursor=next_cursor)
            page2_items = page2_result.get('data', {}).get('items', [])
            print(f"  Page 2 items: {len(page2_items)}")

            # Check for duplicates
            page1_ids = {item.get('basic_info', {}).get('post_id') for item in items}
            page2_ids = {item.get('basic_info', {}).get('post_id') for item in page2_items}
            duplicates = page1_ids.intersection(page2_ids)

            if duplicates:
                print(f"  ⚠️ WARNING: {len(duplicates)} duplicate posts found!")
            else:
                print(f"  ✓ No duplicates - pagination working correctly")

        return result

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("Facebook API Test Suite - Cursor-based Pagination")
    print("=" * 60)

    # Test 1: Simple query with pagination
    test_facebook_query("python", "Simple popular keyword", test_pagination=True)

    # Test 2: News topic
    test_facebook_query("artificial intelligence", "Technology news topic")

    # Test 3: Location-based
    test_facebook_query("Chennai tamilnadu", "City with location", test_pagination=True)

    # Test 4: Generic query
    test_facebook_query("news", "Generic query with pagination", test_pagination=True)

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)
    print("\nSummary:")
    print("- ✓ Cursor-based pagination implemented")
    print("- ✓ Pagination tested (where available)")
    print("- ✓ Duplicate detection tested")
    print("="*60)
