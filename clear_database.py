#!/usr/bin/env python3
"""
Database Cleanup Script
This script deletes ALL data from the YouTube Tracker database.
Use with caution - this action cannot be undone!
"""

import sqlite3
import os
import sys

def confirm_deletion():
    """Ask user for confirmation before proceeding"""
    print("⚠️  WARNING: This will DELETE ALL DATA from your YouTube Tracker database!")
    print("This action cannot be undone.")
    print("\nThis will delete:")
    print("- All video records")
    print("- All channel records") 
    print("- All subscriber history records")
    print("- All linking records")
    
    response = input("\nAre you sure you want to continue? Type 'DELETE ALL' to confirm: ")
    
    return response == "DELETE ALL"

def get_table_counts(conn):
    """Get count of records in each table before deletion"""
    cursor = conn.cursor()
    counts = {}
    
    tables = ['videos', 'channels', 'channel_videos', 'channel_history']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = 0  # Table doesn't exist
    
    return counts

def clear_database():
    """Clear all data from the database"""
    db_file = "videos.db"
    
    # Check if database file exists
    if not os.path.exists(db_file):
        print(f"❌ Database file '{db_file}' not found.")
        print("Make sure you're running this script from the same directory as your app.py file.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Get counts before deletion
        print("📊 Current database contents:")
        counts_before = get_table_counts(conn)
        for table, count in counts_before.items():
            print(f"  {table}: {count} records")
        
        total_records = sum(counts_before.values())
        if total_records == 0:
            print("\n✅ Database is already empty!")
            conn.close()
            return True
        
        print(f"\n🗑️  Deleting {total_records} total records...")
        
        # Delete data from tables (order matters due to foreign keys)
        tables_to_clear = [
            'channel_videos',    # Delete linking table first
            'channel_history',   # Delete history records
            'videos',           # Delete videos
            'channels'          # Delete channels last
        ]
        
        deleted_counts = {}
        
        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table}")
                deleted_counts[table] = cursor.rowcount
                print(f"  ✓ Deleted {cursor.rowcount} records from {table}")
            except sqlite3.OperationalError as e:
                print(f"  ⚠️  Could not clear {table}: {e}")
                deleted_counts[table] = 0
        
        # Reset auto-increment counters
        print("\n🔄 Resetting auto-increment counters...")
        tables_with_autoincrement = ['videos', 'channels', 'channel_history']
        
        for table in tables_with_autoincrement:
            try:
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                print(f"  ✓ Reset counter for {table}")
            except sqlite3.OperationalError:
                pass  # Table might not exist in sqlite_sequence
        
        # Commit changes
        conn.commit()
        
        # Verify deletion
        print("\n🔍 Verifying deletion...")
        counts_after = get_table_counts(conn)
        all_empty = all(count == 0 for count in counts_after.values())
        
        if all_empty:
            print("✅ All data successfully deleted!")
            print("\n📋 Summary:")
            for table in tables_to_clear:
                before = counts_before.get(table, 0)
                deleted = deleted_counts.get(table, 0)
                print(f"  {table}: {before} → 0 (deleted {deleted})")
        else:
            print("⚠️  Some data may still remain:")
            for table, count in counts_after.items():
                if count > 0:
                    print(f"  {table}: {count} records remaining")
        
        conn.close()
        return all_empty
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function"""
    print("🧹 YouTube Tracker Database Cleanup Tool")
    print("=" * 45)
    
    # Ask for confirmation
    if not confirm_deletion():
        print("\n❌ Operation cancelled. No data was deleted.")
        return
    
    print("\n🚀 Starting database cleanup...")
    
    # Clear the database
    success = clear_database()
    
    if success:
        print("\n✅ Database cleanup completed successfully!")
        print("Your database is now empty and ready for fresh data.")
    else:
        print("\n❌ Database cleanup failed!")
        print("Please check the error messages above.")
    
    print("\n" + "=" * 45)

if __name__ == "__main__":
    main()