#!/usr/bin/env python3
"""
Apply news_item_id migration to posts table
"""

import os
from supabase import create_client, Client

def main():
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_service_key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
        return

    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_service_key)

    print("Applying migration: add news_item_id to posts table...")

    try:
        # Execute the migration SQL
        migration_sql = """
        -- Add news_item_id column to posts table
        ALTER TABLE posts ADD COLUMN IF NOT EXISTS news_item_id UUID REFERENCES news_items(id) ON DELETE SET NULL;

        -- Add index for better query performance
        CREATE INDEX IF NOT EXISTS idx_posts_news_item_id ON posts(news_item_id);
        """

        result = supabase.rpc('exec_sql', {'sql': migration_sql}).execute()
        print("Migration applied successfully!")
        print(f"Result: {result}")

    except Exception as e:
        print(f"Migration failed: {e}")
        print("Trying alternative approach...")

        # Try using raw SQL execution if RPC doesn't work
        try:
            # Check if column exists first
            check_result = supabase.rpc('exec_sql', {
                'sql': "SELECT column_name FROM information_schema.columns WHERE table_name = 'posts' AND column_name = 'news_item_id';"
            }).execute()

            if not check_result.data:
                print("news_item_id column doesn't exist, adding it...")
                # Add column
                add_result = supabase.rpc('exec_sql', {
                    'sql': "ALTER TABLE posts ADD COLUMN news_item_id UUID REFERENCES news_items(id) ON DELETE SET NULL;"
                }).execute()
                print(f"Column added: {add_result}")
            else:
                print("news_item_id column already exists!")

        except Exception as e2:
            print(f"Alternative approach also failed: {e2}")
            print("Please apply the migration manually through Supabase dashboard:")
            print("ALTER TABLE posts ADD COLUMN IF NOT EXISTS news_item_id UUID REFERENCES news_items(id) ON DELETE SET NULL;")

if __name__ == "__main__":
    main()