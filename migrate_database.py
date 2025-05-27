#!/usr/bin/env python3
"""
Database Migration Script
Adds video_id column to existing videos table and populates it where possible
"""

import sqlite3
import re

def extract_video_id_from_title_or_description(title, description):
    """
    Try to extract video ID from title or description if it contains a YouTube URL
    This is a fallback method for existing data
    """
    text = f"{title} {description}".lower()
    patterns = [
        r'watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'embed/([a-zA-Z0-9_-]{11})',
        r'shorts/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def migrate_database():
    """Add video_id column and attempt to populate existing records"""
    try:
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()
        
        # Check if video_id column already exists
        cursor.execute("PRAGMA table_info(videos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'video_id' in columns:
            print("✅ video_id column already exists!")
            conn.close()
            return True
        
        print("🔄 Adding video_id column to videos table...")
        
        # Add the video_id column
        cursor.execute("ALTER TABLE videos ADD COLUMN video_id TEXT")
        
        print("✅ video_id column added successfully!")
        
        # Try to populate video_id for existing records (if any URLs are in descriptions)
        print("🔍 Attempting to populate video_id for existing records...")
        
        cursor.execute("SELECT id, title, description FROM videos WHERE video_id IS NULL")
        existing_videos = cursor.fetchall()
        
        updated_count = 0
        for video_id, title, description in existing_videos:
            extracted_id = extract_video_id_from_title_or_description(title or "", description or "")
            if extracted_id:
                cursor.execute("UPDATE videos SET video_id = ? WHERE id = ?", (extracted_id, video_id))
                updated_count += 1
        
        if updated_count > 0:
            print(f"✅ Updated {updated_count} existing records with extracted video IDs")
        else:
            print("ℹ️  No video IDs could be extracted from existing records")
            print("   Existing records will need manual video_id assignment or re-scraping")
        
        # Add unique constraint to video_id column
        print("🔄 Adding unique constraint to video_id column...")
        
        # SQLite doesn't support adding constraints to existing columns easily
        # So we'll create a new table and migrate data
        cursor.execute("""
            CREATE TABLE videos_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                title TEXT,
                description TEXT,
                views INTEGER,
                likes INTEGER,
                comments INTEGER,
                posted TEXT,
                video_length TEXT,
                transcript TEXT,
                saved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                channel_id INTEGER,
                FOREIGN KEY (channel_id) REFERENCES channels(id)
            )
        """)
        
        # Copy data to new table
        cursor.execute("""
            INSERT INTO videos_new (id, video_id, title, description, views, likes, comments, posted, video_length, transcript, saved_at, channel_id)
            SELECT id, video_id, title, description, views, likes, comments, posted, video_length, transcript, saved_at, channel_id
            FROM videos
        """)
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE videos")
        cursor.execute("ALTER TABLE videos_new RENAME TO videos")
        
        print("✅ Unique constraint added to video_id column!")
        
        conn.commit()
        conn.close()
        
        print("\n🎉 Database migration completed successfully!")
        print("   Your database now supports duplicate prevention.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error during migration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {e}")
        return False

def check_migration_needed():
    """Check if migration is needed"""
    try:
        conn = sqlite3.connect("videos.db")
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(videos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        conn.close()
        return 'video_id' not in columns
        
    except Exception as e:
        print(f"Error checking migration status: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 YouTube Tracker Database Migration")
    print("=" * 45)
    
    if not check_migration_needed():
        print("✅ No migration needed - database is already up to date!")
        return
    
    print("🔍 Migration needed - adding duplicate prevention...")
    
    # Backup reminder
    print("\n⚠️  IMPORTANT: Make sure you have a backup of your database!")
    response = input("Continue with migration? (y/N): ")
    
    if response.lower() != 'y':
        print("❌ Migration cancelled.")
        return
    
    # Perform migration
    success = migrate_database()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("   You can now use the duplicate prevention features.")
    else:
        print("\n❌ Migration failed!")
        print("   Please check the error messages above.")

if __name__ == "__main__":
    main()