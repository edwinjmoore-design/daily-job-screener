import os
import asyncio
import csv
import requests
from datetime import datetime
from groq import Groq

# =====================================================
# SECURE ENVIRONMENT VARIABLES
# =====================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# =====================================================
# EDWIN'S PROFILE & RESUME DATA
# =====================================================
my_resume = """
Edwin James Moore
IT Endpoint Technician
Core Competencies: Windows, macOS, Linux, Jamf MDM, TeamDynamix, Office 365, Google Workspace.
Current Location: San Diego County (Must be able to reach school in El Cajon, CA by 2:30 PM PST if hybrid/on-site).
"""

# =====================================================
# LIVE DATA STREAM (FIXED V1 API ENDPOINT)
# =====================================================
def fetch_live_endpoint_jobs():
    app_id = "a2c76e7f"
    app_key = "07dd05920d0d13ce23ebd0570ea7ddd9"
    
    # FIXED: Using the actual Adzuna data API search endpoint
    api_url = "https://adzuna.com"
    
    # BROADENED SEARCH: Captures multiple alternative IT Support job titles
    keywords = '"Endpoint Technician" OR "Desktop Support" OR "IT Support" OR "Help Desk" OR "Helpdesk"'
    
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": keywords,
        "where": "San Diego",
        "distance": 35,          # 35km radius captures surrounding county areas near El Cajon
        "results_per_page": 25   # Casts a wider net to capture more daily listings
    }
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
    except Exception as e:
        print(f"API Connect Error: {e}")
    return []

# =====================================================
# PIPELINE EXECUTION, AI AUDITING & EXCEL EXPORT
# =====================================================
async def main():
    jobs = fetch_live_endpoint_jobs()
    today_str = datetime.now().strftime("%Y_%m_%d")
    csv_filename = "today_jobs.csv"
    csv_headers = ["Job Title", "Company", "Schedule Check", "Salary Check", "Final Verdict", "Apply URL"]
    successful_jobs = []

    # If no jobs are found from the API, write status file and exit cleanly
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

        # UPDATED AI PROMPT: Tight financial targets + clear El Cajon pickup rules
        prompt = f"""
        You are Edwin's personal career advisor auditing an Endpoint Technician role.
        
        EDWIN'S CRITICAL FINANCIAL & LIFESTYLE REQUIREMENTS:
        1. COMPENSATION FLOOR: Target baseline is $60,000+/year. If a job explicitly pays less than $60,000, mark SALARY as FAILED.
        2. CHILDCARE PICKUP WINDOW: He must be off-work, commuted, and at a school in El Cajon, CA by 2:30 PM PST. He must remain free until 6:00 PM PST.
        3. COMMUTE LOGISTICS: The job location is '{location}'. Evaluate if a person can reasonably leave this location and drive to El Cajon, CA by 2:30 PM PST. 
           - If it's a Remote or Hybrid job with flexible hours, it is a high-probability match.
           - If it's on-site in North County (e.g., Oceanside, Carlsbad) or too far to reach El Cajon by 2:30 PM, mark SCHEDULE as FAILED.

        JOB PARAMETERS TO EVALUATE:
        TITLE: {title}
        COMPANY: {company}
        LOCATION: {location}
        DESCRIPTION: {description}

        Provide your output exactly in this clean format:
        SCHEDULE: (PASSED or FAILED) - Short 1-sentence reason regarding the El Cajon 2:30 PM window.
        SALARY: (PASSED or FAILED) - Short 1-sentence reason regarding the $60,000 floor.
        VERDICT: (HIGHLY RECOMMENDED / POTENTIAL MATCH / REJECTED)
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

            # LOOSENED FILTER: Accept top choices AND potential matches for negotiation
            if "HIGHLY RECOMMENDED" in verdict or "POTENTIAL" in verdict:
                successful_jobs.append([title, company, sched_status, sal_status, verdict, apply_link])
        except Exception as e:
            print(f"Error screening job: {e}")

    # Final output router
    if successful_jobs:
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            writer.writerows(successful_jobs)
        print(f"🎉 Success! Generated a match list file with {len(successful_jobs)} roles.")
    else:
        with open("status.txt", "w", encoding="utf-8") as f:
            f.write("Jobs were found on the market today, but our AI screener filtered them out because they conflicted with your 2:30 PM El Cajon childcare window or fell beneath your household income baseline.")
        print("Jobs found, but none passed filters.")

if __name__ == "__main__":
    asyncio.run(main())
