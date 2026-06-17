import os
import asyncio
import csv
from datetime import datetime
import requests
from groq import Groq

# =====================================================
# SECURE ENVIRONMENT VARIABLES
# =====================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

my_resume = """
Edwin James Moore
IT Endpoint Technician
Core Competencies: Windows, macOS, Linux, Jamf MDM, TeamDynamix, Office 365, Google Workspace.
Current Location: San Diego County (Must be able to reach school in El Cajon, CA by 2:30 PM PST if hybrid).
"""

def fetch_live_endpoint_jobs():
    app_id = "a2c76e7f"
    app_key = "07dd05920d0d13ce23ebd0570ea7ddd9"
    base_url = "https://adzuna.com"
    
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": "Endpoint Technician OR Desktop Support OR IT Support Technician",
        "where": "San Diego",  
        "salary_min": 55000,
        "results_per_page": 5
    }

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(base_url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
    except Exception as e:
        print(f"API Connect Error: {e}")
    return []

async def main():
    jobs = fetch_live_endpoint_jobs()
    today_str = datetime.now().strftime("%Y_%m_%d")
    
    csv_filename = "today_jobs.csv"
    csv_headers = ["Job Title", "Company", "Schedule Check", "Salary Check", "Final Verdict", "Apply URL"]
    successful_jobs = []

    # If no jobs are found, create an empty file with an explanation note
    if not jobs:
        with open("status.txt", "w", encoding="utf-8") as f:
            f.write("No new Endpoint Technician roles were posted on Adzuna in San Diego today. We will scan again tomorrow morning!")
        print("No raw listings found today.")
        return

    for job in jobs:
        title = job.get("title", "Unknown")
        company = job.get("company", {}).get("display_name", "Unknown")
        description = job.get("description", "No description.")
        apply_link = job.get("redirect_url", "https://adzuna.com")
        location = job.get("location", {}).get("display_name", "Unknown Location")

        prompt = f"""
        You are Edwin's personal career advisor auditing an Endpoint Technician role.
        
        EDWIN'S ABSOLUTE CONSTRAINTS:
        1. CHILDCARE WINDOW: Must NOT work between 2:00 PM and 6:00 PM PST. 
        2. HYBRID COMMUTE RULE: If the job is hybrid or on-site, evaluate the office location: '{location}'. Is it close enough to San Diego/El Cajon to reasonably log off and pick up his daughter from school in El Cajon, CA by 2:30 PM PST?
        3. COMPENSATION: Target baseline is $60,000+/year.

        JOB PARAMETERS:
        TITLE: {title}
        COMPANY: {company}
        LOCATION: {location}
        DESCRIPTION: {description}

        Provide your output exactly in this clean format:
        SCHEDULE: (PASSED or FAILED) - Short 1-sentence reason
        SALARY: (PASSED or FAILED) - Short 1-sentence reason
        VERDICT: (HIGHLY RECOMMENDED / REJECTED)
        """

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            analysis = response.choices.message.content
            
            sched_status, sal_status, verdict = "Unknown", "Unknown", "REJECTED"
            for line in analysis.split("\n"):
                if "SCHEDULE:" in line: sched_status = line.replace("SCHEDULE:", "").strip()
                if "SALARY:" in line: sal_status = line.replace("SALARY:", "").strip()
                if "VERDICT:" in line: verdict = line.replace("VERDICT:", "").strip()

            if "HIGHLY RECOMMENDED" in verdict:
                successful_jobs.append([title, company, sched_status, sal_status, verdict, apply_link])
                
        except Exception as e:
            print(f"Error screening job: {e}")

    if successful_jobs:
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            writer.writerows(successful_jobs)
    else:
        with open("status.txt", "w", encoding="utf-8") as f:
            f.write("Jobs were found on the market today, but our AI screener filtered them out because they conflicted with your 2 PM childcare window or did not meet your $60k salary target.")

if __name__ == "__main__":
    asyncio.run(main())
