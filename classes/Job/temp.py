# # INSERT_YOUR_CODE

# mock_jobs = [
#     {
#         "title": "Software Engineer",
#         "company": "Techify Inc",
#         "industry": "Information Technology",
#         "description": "Develop and maintain web applications.",
#         "requirements": ["Bachelor's in Computer Science", "Python", "Django", "Problem-solving skills"],
#         "benefits": ["Health insurance", "Remote work", "Stock options"],
#         "rate_per_hour": 40,
#         "hours_per_mo": 160,
#         "available": True
#     },
#     {
#         "title": "Graphic Designer",
#         "company": "Creative Studios",
#         "industry": "Design",
#         "description": "Design marketing materials and graphics for clients.",
#         "requirements": ["Portfolio", "Adobe Creative Suite", "Creativity"],
#         "benefits": ["Flexible hours", "Paid training"],
#         "rate_per_hour": 28,
#         "hours_per_mo": 120,
#         "available": True
#     },
#     {
#         "title": "Data Analyst",
#         "company": "DataWiz",
#         "industry": "Analytics",
#         "description": "Analyze, interpret, and visualize data trends for business solutions.",
#         "requirements": ["SQL", "Excel", "Tableau"],
#         "benefits": ["Health insurance", "Gym allowance"],
#         "rate_per_hour": 35,
#         "hours_per_mo": 140,
#         "available": True
#     },
#     {
#         "title": "Administrative Assistant",
#         "company": "OfficePro",
#         "industry": "Administration",
#         "description": "Manage office schedules and assist in clerical tasks.",
#         "requirements": ["Organizational skills", "Communication", "MS Office"],
#         "benefits": ["Dental insurance", "Paid leaves"],
#         "rate_per_hour": 20,
#         "hours_per_mo": 100,
#         "available": True
#     },
#     {
#         "title": "Sales Representative",
#         "company": "SellRight",
#         "industry": "Sales",
#         "description": "Engage leads and convert prospects to clients.",
#         "requirements": ["Persuasion skills", "CRM knowledge"],
#         "benefits": ["Commission", "Bonuses", "Travel allowance"],
#         "rate_per_hour": 25,
#         "hours_per_mo": 150,
#         "available": True
#     },
#     {
#         "title": "Customer Support Specialist",
#         "company": "HelpHub",
#         "industry": "Customer Service",
#         "description": "Assist users through email and live chat.",
#         "requirements": ["Patience", "Problem-solving", "Excellent communication"],
#         "benefits": ["Health insurance", "Work from home"],
#         "rate_per_hour": 18,
#         "hours_per_mo": 140,
#         "available": True
#     },
#     {
#         "title": "Accountant",
#         "company": "FinSolve",
#         "industry": "Finance",
#         "description": "Manage ledgers, payroll, and financial reports.",
#         "requirements": ["CPA certification", "Quickbooks", "Excel"],
#         "benefits": ["Retirement plan", "Paid holidays"],
#         "rate_per_hour": 32,
#         "hours_per_mo": 160,
#         "available": True
#     },
#     {
#         "title": "HR Recruiter",
#         "company": "HireWell",
#         "industry": "Human Resources",
#         "description": "Source, screen, and interview job candidates.",
#         "requirements": ["Recruiting experience", "Interpersonal skills"],
#         "benefits": ["Bonuses", "Career development"],
#         "rate_per_hour": 27,
#         "hours_per_mo": 130,
#         "available": True
#     },
#     {
#         "title": "Marketing Coordinator",
#         "company": "BrandLaunch",
#         "industry": "Marketing",
#         "description": "Coordinate campaigns and analyze marketing performance.",
#         "requirements": ["Bachelor's in Marketing", "Analytical skills"],
#         "benefits": ["Stock options", "Flexible schedule"],
#         "rate_per_hour": 30,
#         "hours_per_mo": 120,
#         "available": True
#     },
#     {
#         "title": "Warehouse Associate",
#         "company": "LogistiCo",
#         "industry": "Logistics",
#         "description": "Assist with order picking, packing, and shipping tasks.",
#         "requirements": ["Physical fitness", "Attention to detail"],
#         "benefits": ["Health insurance", "Paid overtime"],
#         "rate_per_hour": 17,
#         "hours_per_mo": 180,
#         "available": True
#     },
# ]

# # INSERT_YOUR_CODE
# from classes.Job.index import Job
# from app import db

# for job_data in mock_jobs:
#     job = Job(
#         title=job_data["title"],
#         company=job_data["company"]
#     )
#     job.set_industry(job_data.get("industry"))
#     job.set_description(job_data.get("description"))
#     job.set_requirements(job_data.get("requirements", []))
#     job.set_benefits(job_data.get("benefits", []))
#     job.set_rate_per_hour(job_data.get("rate_per_hour"))
#     job.set_hours_per_month(job_data.get("hours_per_mo"))
#     job.set_available(job_data.get("available", True))
#     job.save_to_db()


