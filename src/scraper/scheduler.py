import os
import json
from datetime import datetime
import shutil
import time
import schedule
from scraper import run_scraper as scraper_main

def rotate_files():
    """Rotate the jobs.json file and maintain historical versions"""
    current_date = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create archive directory if it doesn't exist
    archive_dir = os.path.abspath(os.path.join(base_dir, "../../data/jobs_archive"))
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
    
    # Current jobs.json path
    current_file = os.path.abspath(os.path.join(base_dir, "../../data/jobs_archive/jobs.json"))
    
    # If current jobs.json exists, move it to archive with timestamp
    if os.path.exists(current_file):
        archived_file = os.path.join(archive_dir, f"jobs_{current_date}.json")
        shutil.move(current_file, archived_file)
        print(f"Archived current jobs to: {archived_file}")
    
    return current_file

def cleanup_old_files():
    """Clean up old archived files (keep last 7 days)"""
    archive_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/jobs_archive"))
    if not os.path.exists(archive_dir):
        return
    
    # Get all archived files
    files = os.listdir(archive_dir)
    files = [os.path.join(archive_dir, f) for f in files if f.startswith("jobs_")]
    
    # Sort files by modification time
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    # Keep only the last 7 days of archives (assuming 4 files per day = 28 files)
    files_to_keep = 28
    
    # Remove older files
    for old_file in files[files_to_keep:]:
        os.remove(old_file)
        print(f"Removed old archive: {old_file}")

def run_scraper():
    """Run the scraper and handle file rotation"""
    print(f"\nStarting scraper job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Rotate files first
        current_file = rotate_files()
        
        # Run the scraper
        jobs = scraper_main()
        
        # Save new jobs
        with open(current_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully scraped and saved {len(jobs)} jobs")
        
        # Cleanup old files
        cleanup_old_files()
        
    except Exception as e:
        print(f"Error during scraping: {e}")

def schedule_scraper():
    """Schedule the scraper to run every 6 hours"""
    # Run immediately on start
    run_scraper()
    
    # Schedule to run every 6 hours
    schedule.every(6).hours.do(run_scraper)
    
    print("Scraper scheduled to run every 6 hours")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    schedule_scraper() 