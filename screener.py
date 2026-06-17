import os
import asyncio
import csv
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
import requests
from groq import Groq

# =====================================================
# SECURE ENVIRONMENT VARIABLES
# =====================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MY_EMAIL = os.environ.get("MY_EMAIL")          
MY_PASSWORD = os.environ.get("MY_PASSWORD")    
TARGET_EMAIL = os.environ.get("TARGET_EMAIL")  

client = Groq(api_key=GROQ_API_KEY)

# =====================================================
# EDWIN'S PROFILE
# =====================================================

my_resume = """
Edwin James Moore
IT Endpoint Technician
Core Competencies: Windows, macOS, Linux, Jamf MDM, TeamDynamix, Office 365, Google Workspace.
Current Location: San Diego County (Must be able to reach school in El Cajon, CA by 2:30 PM PST if hybrid).
"""

# =====================================================
# LIVE DATA STREAM 
# =====================================================

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

# =====================================================
# PIPELINE EXECUTION & EXCEL EXPORT
# =====================================================

async def main():
    jobs = fetch_live_endpoint_jobs()
    today_str = datetime.now().strftime("%Y_%m_%d")
    
    # FIXED: If no jobs are found on the API, send a clear status email instead of crashing out early
    if not jobs:
        print("No raw listings found on Adzuna today. Sending status email.")
        send_email_report(None, "No new Endpoint Technician roles were posted on Adzuna in San Diego today. We will scan again tomorrow morning!")
        return

    csv_filename = f"endpoint_jobs_{today_str}.csv"
    csv_headers = ["Job Title", "Company", "Schedule Check", "Salary Check", "Final Verdict", "Apply URL"]
    successful_jobs = []

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
        2. HYBRID COMMUTE RULE: If the job is hybrid or on-site, evaluate the office location: '{location}'. Is it close enough to San Diego/El Cajon to reasonably log off and pick up his daughter from school in El Cajon, CA by 2:30 PM PST? If the commute is too far or unlisted, flag it as a risk.
        3. COMPENSATION: Target baseline is $60,000+/year.
        4. ROLE: Endpoint Support, Hardware Provisioning, Jamf, Windows/macOS.

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

    # FIXED: If jobs existed but none passed the AI schedule/salary constraints
    if successful_jobs:
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            writer.writerows(successful_jobs)
        
        body_text = "Hi Edwin,\n\nAttached is your automated morning IT job spreadsheet. These roles have passed your lifestyle checks."
        send_email_report(csv_filename, body_text)
    else:
        print("Jobs were found, but none passed your lifestyle constraints today.")
        send_email_report(None, "Jobs were found on the market today, but our AI screener filtered them out because they conflicted with your 2 PM childcare window or did not meet your $60k salary target.")

# =====================================================
# FREE AUTOMATED OUTBOUND EMAIL ENGINE
# =====================================================

def send_email_report(filename, body_content):
    print("Preparing automated outbound email transmission...")
    msg = MIMEMultipart()
    msg['From'] = MY_EMAIL
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = f"🎯 Daily IT Job Screener Update - {datetime.now().strftime('%m/%d/%Y')}"
    
    msg.attach(MIMEText(body_content, 'plain'))
    
    if filename and os.path.exists(filename):
        with open(filename, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)
        
    try:
        server = smtplib.SMTP('://gmail.com', 587)
        server.starttls()
        server.login(MY_EMAIL, MY_PASSWORD)
        server.sendmail(MY_EMAIL, TARGET_EMAIL, msg.as_string())
        server.quit()
        print("🎉 Success! Status email delivered to your inbox.")
    except Exception as e:
        print(f"Failed to transmit email: {e}")

if __name__ == "__main__":
    asyncio.run(main())
