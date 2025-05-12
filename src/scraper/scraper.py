#!/usr/bin/env python3

import json
import requests
from bs4 import BeautifulSoup
import re
import concurrent.futures
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class JobData:
    def __init__(self, name, last_date, link, apply_url=""):
        self.name = name
        self.last_date = last_date
        self.link = link
        self.apply_url = apply_url
    
    def to_dict(self):
        return {
            "name": self.name,
            "last_date": self.last_date,
            "link": self.link,
            "apply_url": self.apply_url
        }

def fetch_apply_link_for_scraper(session, job_url):
    """Enhanced apply link fetcher with priority-based detection"""
    try:
        response = session.get(job_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Store different types of links
        apply_links = {
            "apply_online": [],
            "portal": [],
            "website": [],
            "pdf": [],
            "click_here": []
        }
        
        # Find all links
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.text.lower().strip()
            
            # Skip empty links
            if not href or not link_text:
                continue
                
            # Check for direct apply links
            if "apply online" in link_text or "apply now" in link_text:
                apply_links["apply_online"].append(href)
            elif "click here" in link_text:
                # Differentiate between application links and PDF links
                if href.endswith('.pdf'):
                    apply_links["pdf"].append(href)
                else:
                    apply_links["click_here"].append(href)
            # Check for portal links
            elif "portal" in href.lower() or "apply" in href.lower() or "ibps" in href.lower():
                apply_links["portal"].append(href)
            # Check for official website links
            elif "official" in link_text and "website" in link_text:
                apply_links["website"].append(href)
        
        # Return links based on priority
        if apply_links["apply_online"]:
            return apply_links["apply_online"][0]
        if apply_links["portal"]:
            return apply_links["portal"][0]
        if apply_links["website"]:
            return apply_links["website"][0]
        if apply_links["pdf"]:
            return apply_links["pdf"][0]
        if apply_links["click_here"]:
            return apply_links["click_here"][0]
        
        # If no direct links, look for apply-related text
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.text.lower().strip()
            
            if not href or not link_text:
                continue
                
            # Check for text that might indicate apply links
            apply_related_terms = [
                "registration", "application", "apply", "form", "recruitment", "vacancy"
            ]
            
            for term in apply_related_terms:
                if term in link_text:
                    return href
        
        return ""
    except Exception as e:
        logging.error(f"Failed to fetch apply link for {job_url}: {str(e)}")
        return ""

def run_scraper():
    """Main function to run the scraper"""
    # Create session for better performance
    session = requests.Session()
    
    try:
        # Fetch the main page
        response = session.get("https://www.sarkariresult.com/latestjob/", timeout=15)
        response.raise_for_status()
        
        logging.info(f"Successfully fetched main page, status code: {response.status_code}")
        
        # Parse HTML document
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract job listings
        jobs = []
        futures = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Try different selectors to find job entries
            job_cells = soup.select("table tr td")
            logging.info(f"Found {len(job_cells)} table cells with 'table tr td' selector")
            
            if len(job_cells) == 0:
                # Try alternative selectors
                tables = soup.find_all('table')
                logging.info(f"Found {len(tables)} tables on the page")
                
                # Try to find any links on the page
                all_links = soup.find_all('a')
                logging.info(f"Found {len(all_links)} links on the page")
                
                # Get all links with job-like text
                for link in all_links:
                    job_name = link.text.strip()
                    job_url = link.get('href')
                    
                    # Skip empty links or navigation links
                    if not job_url or not job_name or len(job_name) < 10:
                        continue
                        
                    # Skip links that are likely not job listings
                    if "index" in job_url.lower() or "home" in job_url.lower():
                        continue
                    
                    logging.info(f"Found potential job: {job_name}")
                    
                    # Submit task to get apply link
                    future = executor.submit(fetch_apply_link_for_scraper, session, job_url)
                    futures.append((future, job_name, "Not specified", job_url))
            else:
                # Use the original selector logic
                for cell in job_cells:
                    links = cell.find_all('a')
                    for link in links:
                        job_name = link.text.strip()
                        job_url = link.get('href')
                        
                        if job_url and job_name:
                            # Find the "Last Date" text
                            full_text = cell.text
                            last_date = "Not specified"
                            
                            if "Last Date" in full_text:
                                parts = full_text.split("Last Date :")
                                if len(parts) > 1:
                                    date_part = parts[1].strip()
                                    last_date = date_part.split()[0]
                            
                            logging.info(f"Found job: {job_name}")
                            
                            # Submit task to get apply link
                            future = executor.submit(fetch_apply_link_for_scraper, session, job_url)
                            futures.append((future, job_name, last_date, job_url))
            
            # Collect results
            for future, name, date, url in futures:
                try:
                    apply_url = future.result(timeout=15)  # Set timeout for apply link fetch
                    jobs.append(JobData(name, date, url, apply_url))
                    logging.info(f"Added job with apply URL: {apply_url}")
                except Exception as e:
                    logging.error(f"Error getting apply URL for {url}: {str(e)}")
                    # Still add the job but with empty apply URL
                    jobs.append(JobData(name, date, url, ""))
        
        # Convert to list of dictionaries for JSON serialization
        jobs_dict = [job.to_dict() for job in jobs]
        
        logging.info(f"Successfully scraped {len(jobs)} jobs")
        
        return jobs_dict
        
    except Exception as e:
        logging.error(f"Error during scraping: {str(e)}")
        return []

if __name__ == "__main__":
    # When run directly, save to file
    jobs = run_scraper()
    with open("data/jobs_archive/jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    logging.info("Saved jobs to jobs.json") 