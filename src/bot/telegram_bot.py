from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"version compatible with your PTB version, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/"
    )

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
import sys
import os
import json
from datetime import datetime

# Add the python_version_scrap directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../scraper'))
from scraper import run_scraper
import asyncio

# Initialize database
db = Database()

# Replace with your token
TOKEN = '7472288483:AAFG7uDikHbeaI7MV5rx884iBLBQ-AWV_-U'

# Store user states (for pagination and search)
user_states = {}

def get_exam_keyboard():
    keyboard = [
        [InlineKeyboardButton("SSC", callback_data='exam_ssc'),
         InlineKeyboardButton("State Exams", callback_data='exam_state')],
        [InlineKeyboardButton("Private", callback_data='exam_private'),
         InlineKeyboardButton("All Jobs", callback_data='exam_all')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_state_keyboard():
    """Create keyboard for state selection"""
    states = [
        ["Andhra Pradesh", "Arunachal Pradesh"],
        ["Assam", "Bihar"],
        ["Chhattisgarh", "Goa"],
        ["Gujarat", "Haryana"],
        ["Himachal Pradesh", "Jharkhand"],
        ["Karnataka", "Kerala"],
        ["Madhya Pradesh", "Maharashtra"],
        ["Manipur", "Meghalaya"],
        ["Mizoram", "Nagaland"],
        ["Odisha", "Punjab"],
        ["Rajasthan", "Sikkim"],
        ["Tamil Nadu", "Telangana"],
        ["Tripura", "Uttar Pradesh"],
        ["Uttarakhand", "West Bengal"],
        ["Back to Main Menu"]
    ]
    keyboard = [
        [InlineKeyboardButton(state, callback_data=f'state_{state.lower().replace(" ", "_")}') 
         for state in row] if isinstance(row, list) 
        else [InlineKeyboardButton(row, callback_data='back_to_main')]
        for row in states
    ]
    return InlineKeyboardMarkup(keyboard)

def format_job_message(job):
    """Format a single job into a readable message"""
    message = f"🎯 *{job.get('name', 'New Job Opening')}*\n\n"
    
    if job.get('last_date') and job['last_date'] != "Not specified":
        message += f"📅 Last Date: {job['last_date']}\n"
    
    if job.get('link'):
        message += f"🔗 [View Details]({job['link']})\n"
    
    if job.get('apply_url'):
        message += f"📝 [Apply Online]({job['apply_url']})\n"
    
    return message + "\n"

def categorize_job(job_title):
    """Categorize job based on title"""
    title_lower = job_title.lower()
    
    if any(keyword in title_lower for keyword in ['ssc', 'staff selection', 'cgl', 'chsl']):
        return 'ssc'
    elif any(keyword in title_lower for keyword in ['state', 'govt', 'government', 'psc']):
        return 'state'
    else:
        return 'private'

def get_show_more_keyboard(page, has_more):
    """Create keyboard with Show More button if there are more jobs"""
    if has_more:
        keyboard = [[InlineKeyboardButton("📑 Show More Jobs", callback_data=f'more_{page}')]]
        return InlineKeyboardMarkup(keyboard)
    return None

def filter_latest_jobs(jobs, start_idx=0, limit=10):
    """Filter and sort jobs by date"""
    # Convert string dates to datetime objects for sorting
    for job in jobs:
        try:
            if job['last_date'] and job['last_date'] != "Not specified":
                job['date_obj'] = datetime.strptime(job['last_date'], "%d/%m/%Y")
            else:
                job['date_obj'] = datetime.max
        except ValueError:
            job['date_obj'] = datetime.max
    
    # Sort jobs by date (most recent first)
    sorted_jobs = sorted(jobs, key=lambda x: x['date_obj'], reverse=True)
    
    # Return specified slice and whether there are more jobs
    end_idx = start_idx + limit
    return sorted_jobs[start_idx:end_idx], len(sorted_jobs) > end_idx

async def send_jobs_batch(update, jobs, page=0, items_per_page=10):
    """Send a batch of jobs with Show More button if needed"""
    filtered_jobs, has_more = filter_latest_jobs(jobs, page * items_per_page, items_per_page)
    
    if not filtered_jobs:
        await update.message.reply_text(
            "No more jobs available."
        )
        return
    
    message = "📢 Latest Job Notifications:\n\n"
    for job in filtered_jobs:
        message += format_job_message(job)
    
    # Add Show More button if there are more jobs
    reply_markup = get_show_more_keyboard(page + 1, has_more) if has_more else None
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# /start command
async def start(update: Update, context: ContextTypes):
    await update.message.reply_text(
        "🚀 Welcome to JobANI!\n\n"
        "I'll help you stay updated with the latest job notifications.\n\n"
        "Available commands:\n"
        "📝 /subscribe - Get job alerts\n"
        "⚙️ /preferences - Set job preferences\n"
        "📰 /latest - View latest jobs\n"
        "🔍 /search - Search specific jobs\n"
        "🔔 /myalerts - Check your alerts\n"
        "❌ /unsubscribe - Stop alerts\n\n"
        "Let's get started! Use /subscribe to begin."
    )

# /subscribe command
async def subscribe(update: Update, context: ContextTypes):
    user_id = update.effective_user.id
    db.add_user(user_id)
    await update.message.reply_text(
        "✅ Successfully subscribed to job alerts!\n\n"
        "Now, let's set your preferences using /preferences"
    )

# /unsubscribe command
async def unsubscribe(update: Update, context: ContextTypes):
    user_id = update.effective_user.id
    db.remove_user(user_id)
    await update.message.reply_text(
        "❌ You've been unsubscribed from job alerts.\n"
        "You can always subscribe again using /subscribe"
    )

# /preferences command
async def preferences(update: Update, context: ContextTypes):
    await update.message.reply_text(
        "🎯 Select your job preferences:",
        reply_markup=get_exam_keyboard()
    )

# Update button_callback to handle search navigation
async def button_callback(update: Update, context: ContextTypes):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('search_'):
        # Handle search pagination
        user_id = update.effective_user.id
        if user_id not in user_states:
            await query.message.edit_text(
                "Search session expired. Please start a new search with /search."
            )
            return
        
        user_state = user_states[user_id]
        current_page = int(query.data.split('_')[2])
        
        if query.data.startswith('search_next'):
            next_page = current_page + 1
            start_idx = next_page * 5
            end_idx = start_idx + 5
            jobs = user_state['search_results']
            
            if start_idx >= len(jobs):
                await query.answer("No more results!")
                return
            
            current_jobs = jobs[start_idx:end_idx]
            has_more = len(jobs) > end_idx
            
            message = f"🔍 Search Results (showing {start_idx + 1}-{start_idx + len(current_jobs)} of {len(jobs)}):\n\n"
            for job in current_jobs:
                message += format_job_message(job)
            
            # Create keyboard with Next/Previous buttons
            keyboard = []
            if next_page > 0:
                keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f'search_prev_{next_page}'))
            if has_more:
                keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f'search_next_{next_page}'))
            
            reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
            
            await query.message.edit_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            
        elif query.data.startswith('search_prev'):
            prev_page = current_page - 1
            if prev_page < 0:
                await query.answer("Already at first page!")
                return
                
            start_idx = prev_page * 5
            end_idx = start_idx + 5
            jobs = user_state['search_results']
            current_jobs = jobs[start_idx:end_idx]
            has_more = len(jobs) > end_idx
            
            message = f"🔍 Search Results (showing {start_idx + 1}-{start_idx + len(current_jobs)} of {len(jobs)}):\n\n"
            for job in current_jobs:
                message += format_job_message(job)
            
            # Create keyboard with Next/Previous buttons
            keyboard = []
            if prev_page > 0:
                keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f'search_prev_{prev_page}'))
            if has_more:
                keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f'search_next_{prev_page}'))
            
            reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
            
            await query.message.edit_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        return
    
    if query.data.startswith('more_'):
        # Handle Show More button
        page = int(query.data.split('_')[1])
        user_id = update.effective_user.id
        
        try:
            with open("data/jobs_archive/jobs.json", "r") as f:
                jobs = json.load(f)
            
            # Get filtered jobs based on user preferences
            preferences = db.get_user_preferences(user_id)
            selected_type = preferences.get('exam_type') if preferences else None
            selected_state = preferences.get('state') if preferences else None
            
            if selected_type:
                if selected_type == 'state' and selected_state:
                    # Filter by state name
                    jobs = [job for job in jobs if selected_state.lower() in job.get('name', '').lower()]
                else:
                    jobs = [job for job in jobs if categorize_job(job.get('name', '')) == selected_type]
            
            # Get the next batch of jobs
            filtered_jobs, has_more = filter_latest_jobs(jobs, page * 10, 10)
            
            if not filtered_jobs:
                await query.message.edit_text(
                    "No more jobs available."
                )
                return
            
            message = "📢 Latest Job Notifications:\n\n"
            for job in filtered_jobs:
                message += format_job_message(job)
            
            # Add Show More button if there are more jobs
            reply_markup = get_show_more_keyboard(page + 1, has_more) if has_more else None
            
            await query.message.edit_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            print(f"Error loading more jobs: {e}")
            await query.message.edit_text(
                "Sorry, there was an error loading more jobs. Please try again."
            )
        return
    
    # Handle exam type selection
    user_id = update.effective_user.id
    exam_type = query.data.replace('exam_', '')
    
    if exam_type == 'state':
        await query.message.edit_text(
            "📍 Please select your state:",
            reply_markup=get_state_keyboard()
        )
        return
    elif exam_type == 'all':
        db.update_preferences(user_id, {'exam_type': None, 'state': None})
        message = "You'll receive ALL types of job notifications! 🎯"
    else:
        db.update_preferences(user_id, {'exam_type': exam_type, 'state': None})
        message = f"You'll receive notifications for {exam_type.upper()} jobs! 🎯"
    
    await query.message.edit_text(message)

# /latest command
async def latest_jobs(update: Update, context: ContextTypes):
    await update.message.reply_text("🔍 Fetching latest jobs... Please wait.")
    
    try:
        # Read the scraped jobs from jobs.json
        try:
            with open("data/jobs_archive/jobs.json", "r") as f:
                jobs = json.load(f)
        except FileNotFoundError:
            await update.message.reply_text(
                "😕 No jobs data available at the moment.\n"
                "Please try again later!"
            )
            return
        
        if not jobs:
            await update.message.reply_text(
                "😕 No new jobs found at the moment.\n"
                "Please try again later!"
            )
            return
        
        # Get user preferences
        user_id = update.effective_user.id
        preferences = db.get_user_preferences(user_id)
        selected_type = preferences.get('exam_type') if preferences else None
        
        # Filter jobs by user preference if any
        if selected_type:
            jobs = [job for job in jobs if categorize_job(job['name']) == selected_type]
        
        # Send first batch of jobs
        await send_jobs_batch(update, jobs)
        
    except Exception as e:
        print(f"Error in latest_jobs: {e}")
        await update.message.reply_text(
            "😕 Sorry, there was an error fetching the jobs.\n"
            "Please try again later!"
        )

# /myalerts command
async def myalerts(update: Update, context: ContextTypes):
    user_id = update.effective_user.id
    preferences = db.get_user_preferences(user_id)
    
    if not preferences:
        await update.message.reply_text(
            "⚠️ No preferences set!\n"
            "Use /preferences to set your job preferences."
        )
        return
    
    exam_type = preferences.get('exam_type', 'ALL').upper()
    state = preferences.get('state', None)
    
    message = f"🔔 Your Alert Settings:\n\n📑 Job Types: {exam_type}"
    if state:
        message += f"\n🏛️ State: {state}"
    
    message += "\n\nUse /preferences to change your settings."
    await update.message.reply_text(message)

async def search(update: Update, context: ContextTypes):
    """Handle the /search command"""
    if not context.args:
        await update.message.reply_text(
            "Please provide search terms after /search command.\n\n"
            "Examples:\n"
            "- /search UPSC\n"
            "- /search Railway Bihar\n"
            "- /search Teacher Delhi"
        )
        return
    
    search_query = ' '.join(context.args).lower()
    
    try:
        # print("HELLO")
        # Read the latest jobs file
        
        with open("data/jobs_archive/jobs.json", "r") as f:
            all_jobs = json.load(f)
        # print(all_jobs)
        # Search in jobs
        matching_jobs = []
        for job in all_jobs:
            # Search in title and other relevant fields
            job_text = (
                job.get('name', '').lower()
            )
            print(search_query,job_text)
            if search_query in job_text:
                matching_jobs.append(job)
        
        if not matching_jobs:
            await update.message.reply_text(
                f"No jobs found matching '{search_query}'.\n\n"
                "Try different search terms or use /latest to see all jobs."
            )
            return
        
        # Store in user state for pagination
        user_id = update.effective_user.id
        user_states[user_id] = {
            'search_results': matching_jobs,
            'search_query': search_query,
            'page': 0
        }
        
        # Send first batch of results
        await send_search_results(update, matching_jobs, 0)
        
    except FileNotFoundError:
        await update.message.reply_text(
            "😕 No jobs data available at the moment.\n"
            "Please try again later!"
        )
    except Exception as e:
        print(f"Error in search: {e}")
        await update.message.reply_text(
            "Sorry, there was an error processing your search.\n"
            "Please try again later!"
        )

async def send_search_results(update, jobs, page, items_per_page=5):
    """Send search results with pagination"""
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_jobs = jobs[start_idx:end_idx]
    has_more = len(jobs) > end_idx
    
    if not current_jobs:
        await update.message.reply_text("No more results to show.")
        return
    
    message = f"🔍 Search Results (showing {start_idx + 1}-{start_idx + len(current_jobs)} of {len(jobs)}):\n\n"
    
    for job in current_jobs:
        message += format_job_message(job)
    
    # Create keyboard with Next/Previous buttons
    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f'search_prev_{page}'))
    if has_more:
        keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f'search_next_{page}'))
    
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

def main():
    print("Starting JobANI bot...")
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("preferences", preferences))
    app.add_handler(CommandHandler("latest", latest_jobs))
    app.add_handler(CommandHandler("myalerts", myalerts))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("JobANI bot is running!")
    app.run_polling()

if __name__ == '__main__':
    main()
