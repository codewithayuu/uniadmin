import json
import random
import os
from typing import Any, Dict, List

# Constants

DEPARTMENTS = [
    {"dept_id": "DEPT-CS", "name": "Computer Science"},
    {"dept_id": "DEPT-ECE", "name": "Electronics and Communication"},
    {"dept_id": "DEPT-ME", "name": "Mechanical Engineering"},
    {"dept_id": "DEPT-CE", "name": "Civil Engineering"},
    {"dept_id": "DEPT-EE", "name": "Electrical Engineering"},
    {"dept_id": "DEPT-CHE", "name": "Chemical Engineering"},
    {"dept_id": "DEPT-BT", "name": "Biotechnology"},
    {"dept_id": "DEPT-MT", "name": "Mathematics"},
    {"dept_id": "DEPT-PH", "name": "Physics"},
    {"dept_id": "DEPT-CH", "name": "Chemistry"},
    {"dept_id": "DEPT-HS", "name": "Humanities and Social Sciences"},
    {"dept_id": "DEPT-MBA", "name": "Management Studies"},
]

DEPT_IDS = [d["dept_id"] for d in DEPARTMENTS]
DEPT_PREFIXES = {
    "DEPT-CS": "CSE",
    "DEPT-ECE": "ECE",
    "DEPT-ME": "ME",
    "DEPT-CE": "CE",
    "DEPT-EE": "EE",
    "DEPT-CHE": "CHE",
    "DEPT-BT": "BT",
    "DEPT-MT": "MT",
    "DEPT-PH": "PH",
    "DEPT-CH": "CH",
    "DEPT-HS": "HS",
    "DEPT-MBA": "MBA",
}

FIRST_NAMES_MALE = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh",
    "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharva", "Advait", "Dhruv",
    "Kabir", "Ritvik", "Aarush", "Kian", "Darsh", "Veer", "Rohan", "Rahul",
    "Amit", "Suresh", "Vikram", "Nikhil", "Pranav", "Harsh", "Dev", "Raj",
    "Kunal", "Manish", "Ankit", "Deepak", "Gaurav", "Siddharth", "Akash",
    "Varun", "Tarun", "Mohit", "Sahil", "Yash", "Abhishek", "Jayesh",
    "Neeraj", "Piyush", "Ravi", "Sanjay", "Tushar", "Umesh",
]

FIRST_NAMES_FEMALE = [
    "Aanya", "Saanvi", "Myra", "Ananya", "Aadhya", "Aaradhya", "Pari",
    "Anika", "Navya", "Diya", "Kiara", "Avni", "Prisha", "Ira", "Riya",
    "Shreya", "Neha", "Pooja", "Kavya", "Nisha", "Aditi", "Sneha",
    "Meera", "Tanvi", "Ishita", "Sakshi", "Anjali", "Simran", "Komal",
    "Divya", "Swati", "Pallavi", "Radhika", "Sonia", "Tanya", "Urmi",
    "Vandana", "Warda", "Yasmin", "Zara", "Bhavna", "Chitra", "Deepa",
    "Esha", "Falguni", "Garima", "Heena", "Isha", "Jyoti", "Kriti",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Reddy",
    "Nair", "Menon", "Iyer", "Joshi", "Kulkarni", "Deshmukh", "Patil",
    "Shah", "Mehta", "Agarwal", "Banerjee", "Chatterjee", "Das",
    "Ghosh", "Bose", "Sen", "Roy", "Mukherjee", "Pillai", "Rao",
    "Naidu", "Hegde", "Shetty", "Choudhury", "Tiwari", "Pandey",
    "Mishra", "Saxena", "Kapoor", "Khanna", "Malhotra", "Bhatia",
    "Arora",
]

COURSE_NAMES_BY_DEPT = {
    "DEPT-CS": [
        "Data Structures", "Algorithms", "Operating Systems", "Database Systems",
        "Computer Networks", "Machine Learning", "Artificial Intelligence",
        "Software Engineering", "Compiler Design", "Computer Architecture",
        "Distributed Systems", "Cybersecurity",
    ],
    "DEPT-ECE": [
        "Digital Circuits", "Analog Electronics", "Signal Processing",
        "Communication Systems", "VLSI Design", "Embedded Systems",
        "Microprocessors", "Control Systems", "Antenna Theory",
        "Electromagnetic Waves",
    ],
    "DEPT-ME": [
        "Thermodynamics", "Fluid Mechanics", "Strength of Materials",
        "Manufacturing Processes", "Heat Transfer", "Machine Design",
        "CAD/CAM", "Robotics", "IC Engines", "Mechatronics",
    ],
    "DEPT-CE": [
        "Structural Analysis", "Geotechnical Engineering", "Transportation Eng",
        "Hydraulics", "Environmental Engineering", "Surveying",
        "Concrete Technology", "Steel Structures",
    ],
    "DEPT-EE": [
        "Circuit Theory", "Power Systems", "Electrical Machines",
        "Power Electronics", "Control Systems", "Renewable Energy",
        "High Voltage Engineering", "Smart Grid",
    ],
    "DEPT-CHE": [
        "Chemical Kinetics", "Mass Transfer", "Process Control",
        "Reaction Engineering", "Thermodynamics II", "Polymer Engineering",
        "Biochemical Engineering", "Process Design",
    ],
    "DEPT-BT": [
        "Molecular Biology", "Genetics", "Biochemistry", "Bioprocess Eng",
        "Immunology", "Bioinformatics", "Cell Biology", "Microbiology",
    ],
    "DEPT-MT": [
        "Linear Algebra", "Real Analysis", "Probability and Statistics",
        "Numerical Methods", "Discrete Mathematics", "Complex Analysis",
        "Optimization", "Differential Equations",
    ],
    "DEPT-PH": [
        "Classical Mechanics", "Quantum Mechanics", "Electrodynamics",
        "Statistical Mechanics", "Optics", "Nuclear Physics",
        "Solid State Physics", "Astrophysics",
    ],
    "DEPT-CH": [
        "Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry",
        "Analytical Chemistry", "Spectroscopy", "Polymer Chemistry",
        "Environmental Chemistry", "Electrochemistry",
    ],
    "DEPT-HS": [
        "Economics", "Psychology", "Sociology", "Philosophy",
        "Technical Communication", "Ethics in Technology",
    ],
    "DEPT-MBA": [
        "Financial Management", "Marketing Management", "Operations Management",
        "Human Resource Management", "Strategic Management",
        "Business Analytics",
    ],
}

TIME_SLOTS = [
    "09:00-10:30", "10:30-12:00", "12:00-13:30",
    "14:00-15:30", "15:30-17:00",
]

EXAM_DATES = [
    "2025-05-05", "2025-05-06", "2025-05-07", "2025-05-08", "2025-05-09",
    "2025-05-12", "2025-05-13", "2025-05-14", "2025-05-15", "2025-05-16",
    "2025-05-19", "2025-05-20", "2025-05-21", "2025-05-22", "2025-05-23",
]

GRADES = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"]
GRADE_POINTS = {
    "A+": 10.0, "A": 9.0, "A-": 8.5, "B+": 8.0, "B": 7.0,
    "B-": 6.5, "C+": 6.0, "C": 5.0, "C-": 4.5, "D": 4.0, "F": 0.0,
}

SCHOLARSHIP_NAMES = [
    "Merit Excellence Award", "Dean's Scholarship", "National Talent Scholarship",
    "Industry Partner Fellowship", "Research Innovation Grant",
    "Women in STEM Scholarship", "Rural Development Scholarship",
    "Sports Achievement Award", "Community Service Scholarship",
    "International Exchange Grant", "Departmental Topper Award",
    "First Generation Learner Grant", "Economically Weaker Section Scholarship",
    "Alumni Association Scholarship", "Governor's Gold Medal Fund",
    "Technical Innovation Scholarship", "Leadership Excellence Award",
    "Academic Recovery Scholarship", "Diversity and Inclusion Grant",
    "Startup Incubation Scholarship", "Green Technology Award",
    "Digital Literacy Scholarship", "Interdisciplinary Research Grant",
    "Cultural Achievement Award", "Peer Mentoring Scholarship",
    "Publication Incentive Grant", "Hackathon Champion Award",
    "Open Source Contribution Grant", "Teaching Assistant Scholarship",
    "Final Year Project Excellence Award",
]


# Generator Functions

def generate_world() -> Dict[str, Any]:
    """Generate the complete deterministic entity graph.

    Returns a dict with all 14 entity types populated.
    """
    random.seed(42)

    world: Dict[str, Any] = {}

    #  1. Departments (12) ─
    departments = []
    for dept in DEPARTMENTS:
        departments.append({
            "dept_id": dept["dept_id"],
            "name": dept["name"],
            "head_of_dept": None,  # Will be filled after faculty generation
            "courses_offered": [],  # Will be filled after course generation
        })
    world["departments"] = departments

    #  2. Courses (120) 
    courses = []
    course_id_counter = 0

    # Map to track course IDs per department
    dept_course_ids: Dict[str, List[str]] = {d["dept_id"]: [] for d in DEPARTMENTS}

    for dept in DEPARTMENTS:
        dept_id = dept["dept_id"]
        prefix = DEPT_PREFIXES[dept_id]
        dept_courses = COURSE_NAMES_BY_DEPT[dept_id]

        for i, course_name in enumerate(dept_courses):
            course_id_counter += 1
            course_num = 100 + (i + 1) * 10 + random.randint(0, 5)
            course_id = f"{prefix}-{course_num}"

            # Determine prerequisites (later courses require earlier ones)
            prereqs = []
            if i > 0 and random.random() < 0.6:
                prereq_idx = random.randint(0, i - 1)
                prereqs.append(dept_course_ids[dept_id][prereq_idx])

            credits = random.choice([2, 3, 3, 3, 4, 4])
            max_cap = random.choice([30, 40, 50, 60])
            current_enroll = random.randint(5, max_cap - 1)
            semester_offered = random.choice([1, 2, 3, 4, 5, 6, 7, 8])

            courses.append({
                "course_id": course_id,
                "name": course_name,
                "department": dept_id,
                "credits": credits,
                "prerequisites": prereqs,
                "max_capacity": max_cap,
                "current_enrollment": current_enroll,
                "semester_offered": semester_offered,
                "schedule": {
                    "days": random.choice([
                        ["Monday", "Wednesday", "Friday"],
                        ["Tuesday", "Thursday"],
                        ["Monday", "Wednesday"],
                        ["Tuesday", "Thursday", "Saturday"],
                    ]),
                    "time_slot": random.choice(TIME_SLOTS),
                },
            })
            dept_course_ids[dept_id].append(course_id)

    world["courses"] = courses

    # Fill department courses_offered
    for dept in departments:
        dept["courses_offered"] = dept_course_ids[dept["dept_id"]]

    # Build course lookup for quick access
    course_lookup: Dict[str, Dict] = {c["course_id"]: c for c in courses}

    #  3. Faculty (60) ─
    faculty = []
    for fac_idx in range(60):
        fac_id = f"FAC-{fac_idx + 1:03d}"
        dept_id = DEPT_IDS[fac_idx % len(DEPT_IDS)]
        gender = random.choice(["male", "female"])
        if gender == "male":
            fname = random.choice(FIRST_NAMES_MALE)
        else:
            fname = random.choice(FIRST_NAMES_FEMALE)
        lname = random.choice(LAST_NAMES)

        # Assign 1-3 courses from their department
        dept_courses = dept_course_ids.get(dept_id, [])
        num_teaching = min(random.randint(1, 3), len(dept_courses))
        teaching = random.sample(dept_courses, num_teaching) if dept_courses else []

        faculty.append({
            "faculty_id": fac_id,
            "name": f"Dr. {fname} {lname}",
            "department": dept_id,
            "courses_teaching": teaching,
            "office_hours": f"{random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])} {random.choice(TIME_SLOTS)}",
        })

    world["faculty"] = faculty

    # Set department heads (first faculty member per department)
    dept_head_assigned: Dict[str, bool] = {}
    for fac in faculty:
        if fac["department"] not in dept_head_assigned:
            dept_head_assigned[fac["department"]] = True
            for dept in departments:
                if dept["dept_id"] == fac["department"]:
                    dept["head_of_dept"] = fac["faculty_id"]
                    break

    #  4. Students (180) ─
    students = []
    student_genders: Dict[str, str] = {}

    for stu_idx in range(180):
        stu_id = f"STU-{stu_idx + 1:03d}"
        gender = random.choice(["male", "female"])
        student_genders[stu_id] = gender

        if gender == "male":
            fname = random.choice(FIRST_NAMES_MALE)
        else:
            fname = random.choice(FIRST_NAMES_FEMALE)
        lname = random.choice(LAST_NAMES)

        dept_id = random.choice(DEPT_IDS)
        semester = random.randint(1, 8)
        cgpa = round(random.uniform(4.0, 10.0), 2)
        credits_completed = semester * random.randint(15, 22)
        academic_status = "active"
        if cgpa < 5.0:
            academic_status = random.choice(["active", "probation"])

        students.append({
            "student_id": stu_id,
            "name": f"{fname} {lname}",
            "gender": gender,
            "department": dept_id,
            "semester": semester,
            "cgpa": cgpa,
            "credits_completed": credits_completed,
            "academic_status": academic_status,
            "hostel_id": None,  # Will be filled during hostel allocation
        })

    #  Claim deterministic task-specific students without relying on indices 
    claimed_student_ids = set()

    def claim_student(predicate=None):
        for student in students:
            if student["student_id"] in claimed_student_ids:
                continue
            if predicate is None or predicate(student):
                claimed_student_ids.add(student["student_id"])
                return student
        raise RuntimeError("Unable to claim a deterministic student for task setup")

    task5_student = claim_student(lambda s: s["semester"] == 8)
    task5_student.update({
        "name": "Karthik Nair",
        "gender": "male",
        "department": "DEPT-CS",
        "semester": 8,
        "cgpa": 7.50,
        "credits_completed": 155,
        "academic_status": "probation",
        "hostel_id": "RM-A042",
    })
    task5_student_id = task5_student["student_id"]
    student_genders[task5_student_id] = "male"

    task1_student = claim_student(lambda s: s["gender"] == "female")
    task1_student.update({
        "name": "Priya Sharma",
        "gender": "female",
        "department": "DEPT-CS",
        "semester": 5,
        "cgpa": 8.45,
        "credits_completed": 85,
        "academic_status": "active",
        "hostel_id": "RM-E012",
    })
    task1_student_id = task1_student["student_id"]
    student_genders[task1_student_id] = "female"

    task2_student = claim_student(lambda s: s["gender"] == "female")
    task2_student.update({
        "name": "Aanya Patel",
        "gender": "female",
        "department": "DEPT-ECE",
        "semester": 1,
        "cgpa": 0.0,
        "credits_completed": 0,
        "academic_status": "active",
        "hostel_id": None,
    })
    task2_student_id = task2_student["student_id"]
    student_genders[task2_student_id] = "female"

    task3_student = claim_student(lambda s: s["gender"] == "male")
    task3_student.update({
        "name": "Rohan Verma",
        "gender": "male",
        "department": "DEPT-CS",
        "semester": 4,
        "cgpa": 7.80,
        "credits_completed": 68,
        "academic_status": "active",
        "hostel_id": "RM-A015",
    })
    task3_student_id = task3_student["student_id"]
    student_genders[task3_student_id] = "male"

    task4_student_x = claim_student(lambda s: s["gender"] == "male")
    task4_student_x.update({
        "name": "Amit Kumar",
        "gender": "male",
        "department": "DEPT-ECE",
        "semester": 5,
        "cgpa": 7.20,
        "credits_completed": 90,
        "academic_status": "active",
        "hostel_id": "RM-B022",
    })
    task4_student_x_id = task4_student_x["student_id"]
    student_genders[task4_student_x_id] = "male"

    task4_student_y = claim_student(lambda s: s["gender"] == "female")
    task4_student_y.update({
        "name": "Sneha Reddy",
        "gender": "female",
        "department": "DEPT-ECE",
        "semester": 5,
        "cgpa": 9.10,
        "credits_completed": 92,
        "academic_status": "active",
        "hostel_id": "RM-E030",
    })
    task4_student_y_id = task4_student_y["student_id"]
    student_genders[task4_student_y_id] = "female"

    task6_personas = [
        {"name": "Vikram Joshi", "gender": "male", "dept": "DEPT-CS"},
        {"name": "Kavya Menon", "gender": "female", "dept": "DEPT-CS"},
        {"name": "Harsh Pandey", "gender": "male", "dept": "DEPT-ECE"},
        {"name": "Diya Iyer", "gender": "female", "dept": "DEPT-ME"},
        {"name": "Siddharth Roy", "gender": "male", "dept": "DEPT-EE"},
        {"name": "Anjali Das", "gender": "female", "dept": "DEPT-CE"},
        {"name": "Yash Kulkarni", "gender": "male", "dept": "DEPT-CHE"},
        {"name": "Meera Hegde", "gender": "female", "dept": "DEPT-BT"},
    ]
    task6_students = []
    for persona in task6_personas:
        student = claim_student(lambda s, gender=persona["gender"]: s["gender"] == gender)
        student.update({
            "name": persona["name"],
            "gender": persona["gender"],
            "department": persona["dept"],
            "semester": 6,
            "cgpa": round(random.uniform(6.5, 9.0), 2),
            "credits_completed": random.randint(90, 110),
            "academic_status": "active",
            "hostel_id": None,
        })
        student_genders[student["student_id"]] = persona["gender"]
        task6_students.append({
            "id": student["student_id"],
            "name": student["name"],
            "gender": persona["gender"],
            "dept": persona["dept"],
        })

    world["students"] = students

    #  5. Hostel Blocks (8) 
    hostel_blocks = [
        {"block_id": "BLK-A", "name": "Aryabhata Hall", "capacity": 100, "current_occupancy": 75, "gender_restriction": "male"},
        {"block_id": "BLK-B", "name": "Bhabha Hall", "capacity": 100, "current_occupancy": 80, "gender_restriction": "male"},
        {"block_id": "BLK-C", "name": "Chanakya Hall", "capacity": 50, "current_occupancy": 40, "gender_restriction": "male"},
        {"block_id": "BLK-D", "name": "Dhyan Chand Hall", "capacity": 50, "current_occupancy": 45, "gender_restriction": "male"},
        {"block_id": "BLK-E", "name": "Einstein Hall", "capacity": 100, "current_occupancy": 70, "gender_restriction": "female"},
        {"block_id": "BLK-F", "name": "Fatima Hall", "capacity": 100, "current_occupancy": 65, "gender_restriction": "female"},
        {"block_id": "BLK-G", "name": "Gandhi Hall", "capacity": 50, "current_occupancy": 35, "gender_restriction": "female"},
        {"block_id": "BLK-H", "name": "Homi Hall", "capacity": 50, "current_occupancy": 42, "gender_restriction": "female"},
    ]
    world["hostel_blocks"] = hostel_blocks

    #  6. Hostel Rooms (400) ─
    hostel_rooms = []
    room_idx = 0
    block_room_ids: Dict[str, List[str]] = {}

    for block in hostel_blocks:
        block_id = block["block_id"]
        block_letter = block_id.split("-")[1]
        rooms_in_block = block["capacity"] // 2  # 2 per room
        block_room_ids[block_id] = []

        for r in range(rooms_in_block):
            room_idx += 1
            room_id = f"RM-{block_letter}{r + 1:03d}"
            occupant_count = random.choice([0, 1, 1, 2, 2, 2])
            if occupant_count > 2:
                occupant_count = 2
            hostel_rooms.append({
                "room_id": room_id,
                "block_id": block_id,
                "capacity": 2,
                "current_occupants": [],  # Will fill some with student IDs
                "occupant_count": occupant_count,
            })
            block_room_ids[block_id].append(room_id)

    # Ensure specific rooms exist for planted task students
    # RM-E012 for Task 1 student (female, BLK-E)
    for room in hostel_rooms:
        if room["room_id"] == "RM-E012":
            room["current_occupants"] = [task1_student_id]
            room["occupant_count"] = 1
            break

    # RM-A015 for Task 3 student (male, BLK-A)
    for room in hostel_rooms:
        if room["room_id"] == "RM-A015":
            room["current_occupants"] = [task3_student_id]
            room["occupant_count"] = 1
            break

    # RM-B022 for Task 4 scholarship-dependent student
    for room in hostel_rooms:
        if room["room_id"] == "RM-B022":
            room["current_occupants"] = [task4_student_x_id]
            room["occupant_count"] = 1
            break

    # RM-E030 for Task 4 comparison student
    for room in hostel_rooms:
        if room["room_id"] == "RM-E030":
            room["current_occupants"] = [task4_student_y_id]
            room["occupant_count"] = 1
            break

    # RM-A042 for Task 5 student — hostel checkout blocker
    for room in hostel_rooms:
        if room["room_id"] == "RM-A042":
            room["current_occupants"] = [task5_student_id]
            room["occupant_count"] = 1
            break

    # Ensure some female-block rooms have availability for Task 2
    # RM-E001 in BLK-E should have space
    for room in hostel_rooms:
        if room["room_id"] == "RM-E001":
            room["current_occupants"] = []
            room["occupant_count"] = 0
            break

    world["hostel_rooms"] = hostel_rooms

    #  7. Courses specific to tasks 

    # We need to plant specific courses for tasks.
    # Find existing CS courses and ensure we have the right ones.

    # Task 1 needs: CS electives for semester 6 (next sem for the task student in sem 5)
    # Let's ensure some CS courses are offered in semester 6
    cs_courses = [c for c in courses if c["department"] == "DEPT-CS"]

    # Set first 3 CS courses to semester 6 (electives for Task 1)
    if len(cs_courses) >= 3:
        cs_courses[0]["semester_offered"] = 6
        cs_courses[0]["name"] = "Machine Learning"
        cs_courses[0]["credits"] = 4
        cs_courses[0]["max_capacity"] = 40
        cs_courses[0]["current_enrollment"] = 35
        cs_courses[0]["schedule"] = {"days": ["Monday", "Wednesday", "Friday"], "time_slot": "09:00-10:30"}

        cs_courses[1]["semester_offered"] = 6
        cs_courses[1]["name"] = "Distributed Systems"
        cs_courses[1]["credits"] = 3
        cs_courses[1]["max_capacity"] = 30
        cs_courses[1]["current_enrollment"] = 28
        cs_courses[1]["schedule"] = {"days": ["Tuesday", "Thursday"], "time_slot": "10:30-12:00"}

        cs_courses[2]["semester_offered"] = 6
        cs_courses[2]["name"] = "Cybersecurity"
        cs_courses[2]["credits"] = 3
        cs_courses[2]["max_capacity"] = 50
        cs_courses[2]["current_enrollment"] = 30
        cs_courses[2]["schedule"] = {"days": ["Monday", "Wednesday"], "time_slot": "14:00-15:30"}

    # Ensure a CS course conflicts with the Task 1 student's current schedule
    if len(cs_courses) >= 5:
        cs_courses[3]["semester_offered"] = 6
        cs_courses[3]["name"] = "Artificial Intelligence"
        cs_courses[3]["credits"] = 4
        cs_courses[3]["max_capacity"] = 40
        cs_courses[3]["current_enrollment"] = 39  # Only 1 seat
        cs_courses[3]["schedule"] = {"days": ["Tuesday", "Thursday"], "time_slot": "10:30-12:00"}
        # Same schedule as cs_courses[1] — conflict!

        cs_courses[4]["semester_offered"] = 6
        cs_courses[4]["name"] = "Compiler Design"
        cs_courses[4]["credits"] = 4
        cs_courses[4]["prerequisites"] = [cs_courses[0]["course_id"]]  # Requires ML
        cs_courses[4]["max_capacity"] = 30
        cs_courses[4]["current_enrollment"] = 5
        cs_courses[4]["schedule"] = {"days": ["Wednesday", "Friday"], "time_slot": "15:30-17:00"}

    # Task 3: Course A (currently enrolled) and Course B (target)
    # The task student wants to switch from Course A to Course B
    # Course A: a CS course STU-088 is in
    # Course B: another CS course with prerequisites
    task3_course_a_id = cs_courses[0]["course_id"] if cs_courses else "CSE-110"
    task3_course_b_id = cs_courses[2]["course_id"] if len(cs_courses) > 2 else "CSE-130"

    # Ensure Course B has a prerequisite pattern that makes the switch feasible
    if len(cs_courses) > 2:
        cs_courses[2]["prerequisites"] = []  # No prereq for course B — make switch feasible
        cs_courses[2]["max_capacity"] = 50
        cs_courses[2]["current_enrollment"] = 45  # 5 seats available

    # Task 4: ECE-201 with exactly 1 seat remaining
    ece_courses = [c for c in courses if c["department"] == "DEPT-ECE"]
    task4_course_id = None
    if ece_courses:
        ece_courses[0]["course_id"] = ece_courses[0]["course_id"]  # Keep existing ID
        task4_course_id = ece_courses[0]["course_id"]
        ece_courses[0]["name"] = "VLSI Design"
        ece_courses[0]["max_capacity"] = 40
        ece_courses[0]["current_enrollment"] = 39  # Exactly 1 seat
        ece_courses[0]["credits"] = 4
        ece_courses[0]["semester_offered"] = 5
        ece_courses[0]["prerequisites"] = []

    # Task 5: Capstone course for the graduation-crisis student
    # Also need an elective he needs for the 2 missing credits
    if len(cs_courses) >= 8:
        # Capstone course
        cs_courses[5]["semester_offered"] = 8
        cs_courses[5]["name"] = "Capstone Project"
        cs_courses[5]["credits"] = 4
        cs_courses[5]["max_capacity"] = 30
        cs_courses[5]["current_enrollment"] = 15
        cs_courses[5]["prerequisites"] = [cs_courses[6]["course_id"]]  # Requires Software Eng
        cs_courses[5]["schedule"] = {"days": ["Monday", "Wednesday", "Friday"], "time_slot": "09:00-10:30"}

        # Software Engineering — the prerequisite Karthik is missing
        cs_courses[6]["semester_offered"] = 7
        cs_courses[6]["name"] = "Software Engineering"
        cs_courses[6]["credits"] = 3

        # An equivalent course Karthik completed with B+ (for waiver)
        cs_courses[7]["semester_offered"] = 6
        cs_courses[7]["name"] = "Software Design Patterns"
        cs_courses[7]["credits"] = 3

        # Elective for the missing 2 credits
        if len(cs_courses) >= 10:
            cs_courses[8]["semester_offered"] = 8
            cs_courses[8]["name"] = "Advanced Algorithms"
            cs_courses[8]["credits"] = 3
            cs_courses[8]["max_capacity"] = 40
            cs_courses[8]["current_enrollment"] = 20
            cs_courses[8]["prerequisites"] = []
            cs_courses[8]["schedule"] = {"days": ["Tuesday", "Thursday"], "time_slot": "14:00-15:30"}

    world["courses"] = courses

    #  8. Enrollments (2000) ─
    enrollments = []
    enr_counter = 0
    student_current_enrollments: Dict[str, List[str]] = {s["student_id"]: [] for s in students}

    # Plant specific enrollments for task students first

    # Task 1 student current enrollments (semester 5 CS courses)
    task1_current_courses = []
    non_sem6_cs = [c for c in cs_courses if c["semester_offered"] != 6]
    for c in non_sem6_cs[:4]:  # 4 current courses
        enr_counter += 1
        enrollments.append({
            "enrollment_id": f"ENR-{enr_counter:05d}",
            "student_id": task1_student_id,
            "course_id": c["course_id"],
            "semester": 5,
            "grade": None,  # Current semester — no grade yet
            "status": "enrolled",
        })
        student_current_enrollments[task1_student_id].append(c["course_id"])
        task1_current_courses.append(c["course_id"])

    # Give the Task 1 student a course with a conflicting schedule (Tues/Thurs 10:30-12:00)
    # to make the conflict detection meaningful
    for c in courses:
        if c["department"] != "DEPT-CS" and c.get("schedule", {}).get("time_slot") == "10:30-12:00":
            if "Tuesday" in c.get("schedule", {}).get("days", []) or "Thursday" in c.get("schedule", {}).get("days", []):
                enr_counter += 1
                enrollments.append({
                    "enrollment_id": f"ENR-{enr_counter:05d}",
                    "student_id": task1_student_id,
                    "course_id": c["course_id"],
                    "semester": 5,
                    "grade": None,
                    "status": "enrolled",
                })
                student_current_enrollments[task1_student_id].append(c["course_id"])
                break

    # Task 3 student enrolled in Course A
    enr_counter += 1
    enrollments.append({
        "enrollment_id": f"ENR-{enr_counter:05d}",
        "student_id": task3_student_id,
        "course_id": task3_course_a_id,
        "semester": 4,
        "grade": None,
        "status": "enrolled",
    })
    student_current_enrollments[task3_student_id].append(task3_course_a_id)

    # Give the Task 3 student a few more courses
    other_courses_for_088 = [c["course_id"] for c in courses
                             if c["department"] == "DEPT-CS"
                             and c["course_id"] != task3_course_a_id
                             and c["course_id"] != task3_course_b_id
                             and c["semester_offered"] <= 4][:3]
    for cid in other_courses_for_088:
        enr_counter += 1
        enrollments.append({
            "enrollment_id": f"ENR-{enr_counter:05d}",
            "student_id": task3_student_id,
            "course_id": cid,
            "semester": 4,
            "grade": None,
            "status": "enrolled",
        })
        student_current_enrollments[task3_student_id].append(cid)

    # Task 5: Karthik's enrollments
    # He needs to be enrolled in courses totaling credits near the limit
    # Also needs past enrollment in "Software Design Patterns" with grade B+ (for waiver)
    karthik_current_courses = []
    if len(cs_courses) >= 10:
        # Current semester enrollments (semester 8)
        for c in [cs_courses[5]]:  # Capstone — he wants to enroll but has prereq issue
            pass  # He's NOT enrolled yet — he needs to enroll

        # Past enrollment: Software Design Patterns with B+ (equivalent course for waiver)
        enr_counter += 1
        enrollments.append({
            "enrollment_id": f"ENR-{enr_counter:05d}",
            "student_id": task5_student_id,
            "course_id": cs_courses[7]["course_id"],  # Software Design Patterns
            "semester": 6,
            "grade": "B+",
            "status": "completed",
        })

        # Current semester: some courses totaling near credit limit (21)
        # Give him 18 credits of current courses (needs 3 more = the elective)
        credit_so_far = 0
        for c in courses:
            if (c["department"] == "DEPT-CS"
                    and c["semester_offered"] == 8
                    and c["course_id"] != cs_courses[5]["course_id"]
                    and c["course_id"] != cs_courses[8]["course_id"]
                    and credit_so_far + c["credits"] <= 18):
                enr_counter += 1
                enrollments.append({
                    "enrollment_id": f"ENR-{enr_counter:05d}",
                    "student_id": task5_student_id,
                    "course_id": c["course_id"],
                    "semester": 8,
                    "grade": None,
                    "status": "enrolled",
                })
                student_current_enrollments[task5_student_id].append(c["course_id"])
                karthik_current_courses.append(c["course_id"])
                credit_so_far += c["credits"]
                if credit_so_far >= 16:
                    break

        # If we don't have enough CS sem-8 courses, use other dept courses
        if credit_so_far < 16:
            for c in courses:
                if (c["course_id"] not in student_current_enrollments[task5_student_id]
                        and c["semester_offered"] == 8
                        and credit_so_far + c["credits"] <= 19):
                    enr_counter += 1
                    enrollments.append({
                        "enrollment_id": f"ENR-{enr_counter:05d}",
                        "student_id": task5_student_id,
                        "course_id": c["course_id"],
                        "semester": 8,
                        "grade": None,
                        "status": "enrolled",
                    })
                    student_current_enrollments[task5_student_id].append(c["course_id"])
                    karthik_current_courses.append(c["course_id"])
                    credit_so_far += c["credits"]
                    if credit_so_far >= 16:
                        break

        # Past completed courses for Karthik (semesters 1-7)
        past_count = 0
        for c in courses:
            if (c["course_id"] not in student_current_enrollments[task5_student_id]
                    and c["course_id"] != cs_courses[7]["course_id"]
                    and c["semester_offered"] < 8
                    and past_count < 30):
                enr_counter += 1
                grade = random.choice(["A", "A-", "B+", "B", "B-", "C+", "C"])
                enrollments.append({
                    "enrollment_id": f"ENR-{enr_counter:05d}",
                    "student_id": task5_student_id,
                    "course_id": c["course_id"],
                    "semester": c["semester_offered"],
                    "grade": grade,
                    "status": "completed",
                })
                past_count += 1

    # Task 6: Enroll the 8 students in courses that will have exam conflicts
    # (We'll set up the exam conflicts in the exam schedule section)
    task6_course_pairs = []
    available_courses = [c for c in courses if c["current_enrollment"] < c["max_capacity"]]
    for i, ts in enumerate(task6_students):
        # Each student needs at least 2 courses with conflicting exams
        if len(available_courses) >= 2 * (i + 1):
            c1 = available_courses[2 * i]
            c2 = available_courses[2 * i + 1]
            task6_course_pairs.append((ts["id"], c1["course_id"], c2["course_id"]))

            for cid in [c1["course_id"], c2["course_id"]]:
                enr_counter += 1
                enrollments.append({
                    "enrollment_id": f"ENR-{enr_counter:05d}",
                    "student_id": ts["id"],
                    "course_id": cid,
                    "semester": 6,
                    "grade": None,
                    "status": "enrolled",
                })
                student_current_enrollments[ts["id"]].append(cid)

    # Generate remaining enrollments for other students to reach ~2000
    remaining_students = [s for s in students
                          if s["student_id"] not in
                          {task1_student_id, task2_student_id, task3_student_id,
                           task4_student_x_id, task4_student_y_id, task5_student_id,
                           *[student["id"] for student in task6_students]}]

    for stu in remaining_students:
        if enr_counter >= 2000:
            break
        dept_courses = [c for c in courses if c["department"] == stu["department"]]
        if not dept_courses:
            dept_courses = courses[:5]

        # Current semester: 3-5 courses
        num_current = random.randint(3, min(5, len(dept_courses)))
        chosen = random.sample(dept_courses, min(num_current, len(dept_courses)))

        for c in chosen:
            if enr_counter >= 2000:
                break
            enr_counter += 1
            enrollments.append({
                "enrollment_id": f"ENR-{enr_counter:05d}",
                "student_id": stu["student_id"],
                "course_id": c["course_id"],
                "semester": stu["semester"],
                "grade": None if random.random() < 0.3 else random.choice(GRADES[:7]),
                "status": random.choice(["enrolled", "completed", "completed"]),
            })
            student_current_enrollments[stu["student_id"]].append(c["course_id"])

    world["enrollments"] = enrollments

    #  9. Fee Records (one per student) ─
    fee_records = []
    for i, stu in enumerate(students):
        fee_id = f"FEE-{i + 1:03d}"
        base_fee = random.choice([50000, 75000, 100000, 125000])
        amount_paid = base_fee  # Most students are paid up
        amount_due = 0

        fee_records.append({
            "record_id": fee_id,
            "student_id": stu["student_id"],
            "amount_due": amount_due,
            "amount_paid": amount_paid,
            "total_fee": base_fee,
            "due_date": "2025-04-30",
            "status": "paid",
        })

    # Task 2 student fees are paid (no blocker)
    for fr in fee_records:
        if fr["student_id"] == task2_student_id:
            fr["status"] = "paid"
            fr["amount_due"] = 0
            fr["amount_paid"] = 75000
            fr["total_fee"] = 75000
            break

    # Task 5 student has unpaid fee of ₹2,500 (Blocker 2)
    for fr in fee_records:
        if fr["student_id"] == task5_student_id:
            fr["amount_due"] = 2500
            fr["amount_paid"] = 97500
            fr["total_fee"] = 100000
            fr["status"] = "partial"
            break

    world["fee_records"] = fee_records

    #  10. Scholarships (30) 
    scholarships = []
    for i in range(30):
        sch_id = f"SCH-{i + 1:03d}"
        min_cgpa = round(random.uniform(6.0, 8.5), 1)
        min_credits = random.randint(60, 120)
        amount = random.choice([10000, 20000, 25000, 50000, 75000, 100000])

        beneficiaries = []
        # Randomly assign 2-5 beneficiary students
        num_beneficiaries = random.randint(2, 5)
        eligible_students = [s["student_id"] for s in students
                             if s["cgpa"] >= min_cgpa
                             and s["credits_completed"] >= min_credits]
        if eligible_students:
            beneficiaries = random.sample(eligible_students,
                                          min(num_beneficiaries, len(eligible_students)))

        scholarships.append({
            "scholarship_id": sch_id,
            "name": SCHOLARSHIP_NAMES[i],
            "criteria": f"Minimum CGPA {min_cgpa}, minimum {min_credits} credits completed",
            "min_cgpa": min_cgpa,
            "min_credits": min_credits,
            "amount": amount,
            "beneficiaries": beneficiaries,
        })

    # Task 3 student has a scholarship with min credit requirement
    # The scholarship requires at least 16 credits this semester
    scholarships[0] = {
        "scholarship_id": "SCH-001",
        "name": "Merit Excellence Award",
        "criteria": "Minimum CGPA 7.0, minimum 60 credits completed, must maintain 16 credits per semester",
        "min_cgpa": 7.0,
        "min_credits": 60,
        "min_semester_credits": 16,
        "amount": 50000,
        "beneficiaries": [task3_student_id],
        "required_courses": [],
    }

    # Task 4 priority student has a scholarship that REQUIRES the specific ECE course
    scholarships[1] = {
        "scholarship_id": "SCH-002",
        "name": "Industry Partner Fellowship",
        "criteria": "Must be enrolled in VLSI Design course as part of scholarship agreement",
        "min_cgpa": 7.0,
        "min_credits": 80,
        "amount": 75000,
        "beneficiaries": [task4_student_x_id],
        "required_courses": [task4_course_id] if task4_course_id else [],
    }

    # Task 5 student has a scholarship with minimum credit requirement (Blocker 4)
    scholarships[2] = {
        "scholarship_id": "SCH-003",
        "name": "Dean's Scholarship",
        "criteria": "Minimum CGPA 7.0, must maintain at least 15 credits per semester",
        "min_cgpa": 7.0,
        "min_credits": 100,
        "min_semester_credits": 15,
        "amount": 100000,
        "beneficiaries": [task5_student_id],
        "required_courses": [],
    }

    world["scholarships"] = scholarships

    #  11. Exam Schedule (200) ─
    exam_schedule = []
    exam_counter = 0

    # Room IDs for exam halls (reuse some hostel rooms + dedicated exam rooms)
    exam_room_ids = [f"EXAM-{r + 1:03d}" for r in range(20)]

    # Generate exams for most courses
    courses_with_exams = random.sample(courses, min(200, len(courses)))

    for c in courses_with_exams:
        exam_counter += 1
        exam_id = f"EXM-{exam_counter:03d}"
        date = random.choice(EXAM_DATES)
        time_slot = random.choice(TIME_SLOTS)
        room = random.choice(exam_room_ids)

        # Find a faculty member from the same department
        dept_faculty = [f for f in faculty if f["department"] == c["department"]]
        invigilator = dept_faculty[0]["faculty_id"] if dept_faculty else faculty[0]["faculty_id"]

        exam_schedule.append({
            "exam_id": exam_id,
            "course_id": c["course_id"],
            "date": date,
            "time_slot": time_slot,
            "room_id": room,
            "faculty_invigilator": invigilator,
        })

    # Task 6: Plant exam conflicts for the 8 students
    # Each pair of courses for a student should have the SAME date + time_slot
    for stu_id, c1_id, c2_id in task6_course_pairs:
        conflict_date = random.choice(EXAM_DATES)
        conflict_slot = random.choice(TIME_SLOTS)

        # Find or create exam for c1
        existing_c1 = [e for e in exam_schedule if e["course_id"] == c1_id]
        if existing_c1:
            existing_c1[0]["date"] = conflict_date
            existing_c1[0]["time_slot"] = conflict_slot
        else:
            exam_counter += 1
            dept_for_c1 = course_lookup.get(c1_id, {}).get("department", "DEPT-CS")
            dept_fac = [f for f in faculty if f["department"] == dept_for_c1]
            exam_schedule.append({
                "exam_id": f"EXM-{exam_counter:03d}",
                "course_id": c1_id,
                "date": conflict_date,
                "time_slot": conflict_slot,
                "room_id": random.choice(exam_room_ids),
                "faculty_invigilator": dept_fac[0]["faculty_id"] if dept_fac else "FAC-001",
            })

        # Find or create exam for c2
        existing_c2 = [e for e in exam_schedule if e["course_id"] == c2_id]
        if existing_c2:
            existing_c2[0]["date"] = conflict_date
            existing_c2[0]["time_slot"] = conflict_slot
        else:
            exam_counter += 1
            dept_for_c2 = course_lookup.get(c2_id, {}).get("department", "DEPT-CS")
            dept_fac = [f for f in faculty if f["department"] == dept_for_c2]
            exam_schedule.append({
                "exam_id": f"EXM-{exam_counter:03d}",
                "course_id": c2_id,
                "date": conflict_date,
                "time_slot": conflict_slot,
                "room_id": random.choice(exam_room_ids),
                "faculty_invigilator": dept_fac[0]["faculty_id"] if dept_fac else "FAC-001",
            })

    # Pad to ~200 exams if needed
    while exam_counter < 200:
        exam_counter += 1
        c = random.choice(courses)
        dept_fac = [f for f in faculty if f["department"] == c["department"]]
        exam_schedule.append({
            "exam_id": f"EXM-{exam_counter:03d}",
            "course_id": c["course_id"],
            "date": random.choice(EXAM_DATES),
            "time_slot": random.choice(TIME_SLOTS),
            "room_id": random.choice(exam_room_ids),
            "faculty_invigilator": dept_fac[0]["faculty_id"] if dept_fac else "FAC-001",
        })

    world["exam_schedule"] = exam_schedule

    #  12. Regulations (25) ─
    regulations = [
        {
            "reg_id": "REG-001",
            "title": "Maximum Credit Limit Per Semester",
            "description": "Students may enroll in a maximum of 21 credits per semester. Exception: graduating students in final semester may enroll up to 24 credits with approval.",
            "applicable_to": "student",
            "conditions": {"max_credits": 21, "exception_max_credits": 24, "exception_condition": "final_semester_graduating"},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-002",
            "title": "Prerequisite Enforcement",
            "description": "Students must complete all listed prerequisites before enrolling in a course. Waiver available if student completed an equivalent course with grade B or better.",
            "applicable_to": "course",
            "conditions": {"waiver_min_grade": "B", "waiver_type": "equivalent_course"},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-003",
            "title": "Add/Drop Deadline",
            "description": "Course add/drop requests must be submitted before the semester add/drop deadline. After the deadline, enrollment and drop operations are locked.",
            "applicable_to": "course",
            "conditions": {"deadline_enforced": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-004",
            "title": "Fee Clearance for Enrollment",
            "description": "Students with outstanding fees exceeding ₹0 are blocked from new course enrollments and hostel allocations until fees are cleared.",
            "applicable_to": "student",
            "conditions": {"max_outstanding": 0},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-005",
            "title": "Hostel Gender Restriction",
            "description": "Students may only be allocated to hostel blocks matching their gender designation. Male students to male blocks, female students to female blocks.",
            "applicable_to": "hostel",
            "conditions": {"gender_match_required": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-006",
            "title": "Scholarship Minimum Credit Maintenance",
            "description": "Students receiving scholarships must maintain a minimum credit load per semester as specified in their scholarship agreement. Dropping below triggers scholarship review.",
            "applicable_to": "student",
            "conditions": {"triggers_review": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-007",
            "title": "Academic Probation Restrictions",
            "description": "Students on academic probation may not enroll in more than 15 credits per semester and must receive faculty advisor approval for course changes.",
            "applicable_to": "student",
            "conditions": {"probation_credit_limit": 15, "advisor_approval_required": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-008",
            "title": "Graduation Credit Requirement",
            "description": "Students must complete a minimum of 160 credits to be eligible for graduation. Department-specific requirements may apply in addition.",
            "applicable_to": "student",
            "conditions": {"min_graduation_credits": 160},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-009",
            "title": "Hostel Checkout Deadline",
            "description": "Graduating students must initiate hostel checkout by April 30th. Failure to initiate checkout blocks graduation clearance.",
            "applicable_to": "hostel",
            "conditions": {"checkout_deadline": "2025-04-30", "blocks_graduation": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-010",
            "title": "Exam Schedule Conflict Resolution",
            "description": "If a student has two exams scheduled at the same date and time, the department must reschedule one exam to a non-conflicting slot. No student may have two exams on the same day.",
            "applicable_to": "exam",
            "conditions": {"no_same_day_exams": True, "department_resolves": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-011",
            "title": "Scholarship Priority in Enrollment",
            "description": "When enrollment capacity is limited, students with scholarship dependencies on a specific course receive priority over merit-based ordering (CGPA).",
            "applicable_to": "course",
            "conditions": {"scholarship_priority": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-012",
            "title": "Fee Deferral Policy",
            "description": "Fee deferral is available only to students with an active scholarship covering at least 50% of their total fees.",
            "applicable_to": "student",
            "conditions": {"min_scholarship_coverage": 0.5},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-013",
            "title": "Credit Overload Exception",
            "description": "Credit overload exception is approved ONLY if student is in final semester AND short 3 or fewer credits of the graduation requirement.",
            "applicable_to": "student",
            "conditions": {"final_semester_only": True, "max_credit_shortfall": 3},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-014",
            "title": "Prerequisite Waiver Policy",
            "description": "Prerequisite waiver is approved ONLY if the student has completed an equivalent course with grade B or better.",
            "applicable_to": "course",
            "conditions": {"min_equivalent_grade": "B", "equivalent_course_required": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-015",
            "title": "Academic Probation Clearance",
            "description": "Academic probation status should be cleared when a student's CGPA recovers to 6.0 or above for two consecutive semesters.",
            "applicable_to": "student",
            "conditions": {"clearance_cgpa": 6.0, "consecutive_semesters": 2},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-016",
            "title": "Hostel Room Capacity Limit",
            "description": "Each hostel room has a maximum capacity of 2 students. No room may exceed this capacity.",
            "applicable_to": "hostel",
            "conditions": {"max_room_capacity": 2},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-017",
            "title": "Enrollment Seat Capacity",
            "description": "Course enrollment may not exceed the stated maximum capacity. When a course is full, no additional enrollments are accepted.",
            "applicable_to": "course",
            "conditions": {"strict_capacity": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-018",
            "title": "Minimum CGPA for Course Registration",
            "description": "Students with CGPA below 4.0 are not permitted to register for new courses until they complete remedial requirements.",
            "applicable_to": "student",
            "conditions": {"min_registration_cgpa": 4.0},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-019",
            "title": "Faculty Invigilator Availability",
            "description": "Each exam must have an assigned faculty invigilator. A faculty member may not invigilate two exams at the same date and time.",
            "applicable_to": "exam",
            "conditions": {"one_invigilator_per_slot": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-020",
            "title": "Exam Room Capacity",
            "description": "Each exam room has a maximum seating capacity. No exam may be assigned to a room that is already booked for the same date and time slot.",
            "applicable_to": "exam",
            "conditions": {"no_double_booking": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-021",
            "title": "Course Drop Impact on CGPA",
            "description": "Dropping a course after the midterm period results in a 'W' (withdrawal) grade recorded on the transcript, which does not affect CGPA.",
            "applicable_to": "course",
            "conditions": {"post_midterm_withdrawal_grade": "W"},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-022",
            "title": "Inter-Department Enrollment",
            "description": "Students may enroll in courses from other departments as electives, subject to the same prerequisite and capacity rules.",
            "applicable_to": "course",
            "conditions": {"cross_department_allowed": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-023",
            "title": "Payment Recording Policy",
            "description": "All fee payments must be recorded immediately. Partial payments are accepted and reduce the outstanding balance accordingly.",
            "applicable_to": "student",
            "conditions": {"partial_payments_accepted": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-024",
            "title": "Hostel Transfer Policy",
            "description": "Hostel transfers require fee clearance and the target room must have available capacity. Transfers between gender-restricted blocks follow gender matching rules.",
            "applicable_to": "hostel",
            "conditions": {"fee_clearance_required": True, "gender_match_required": True},
            "effective_date": "2024-01-01",
        },
        {
            "reg_id": "REG-025",
            "title": "Duplicate Enrollment Prevention",
            "description": "A student may not be enrolled in the same course more than once in the same semester. Duplicate enrollment attempts are rejected.",
            "applicable_to": "course",
            "conditions": {"no_duplicates": True},
            "effective_date": "2024-01-01",
        },
    ]
    world["regulations"] = regulations

    #  13. Exceptions (15) 
    exceptions = [
        {
            "exception_id": "EXC-001",
            "type": "credit_overload",
            "eligibility_conditions": "Student must be in final semester AND short ≤3 credits of graduation requirement (160 credits)",
            "approval_rules": {"final_semester": True, "max_shortfall": 3, "graduation_credits": 160},
        },
        {
            "exception_id": "EXC-002",
            "type": "prerequisite_waiver",
            "eligibility_conditions": "Student must have completed an equivalent course with grade B or better",
            "approval_rules": {"min_equivalent_grade": "B", "equivalent_course_required": True},
        },
        {
            "exception_id": "EXC-003",
            "type": "fee_deferral",
            "eligibility_conditions": "Student must have an active scholarship covering ≥50% of total fees",
            "approval_rules": {"min_scholarship_coverage": 0.5},
        },
        {
            "exception_id": "EXC-004",
            "type": "capacity_override",
            "eligibility_conditions": "Not available — capacity overrides are not permitted",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-005",
            "type": "gender_block_override",
            "eligibility_conditions": "Not available — gender restrictions are not waivable",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-006",
            "type": "deadline_extension",
            "eligibility_conditions": "Not available — deadline extensions are not permitted",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-007",
            "type": "probation_enrollment",
            "eligibility_conditions": "Not available — probation enrollment limits are not waivable",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-008",
            "type": "graduation_credit_shortfall",
            "eligibility_conditions": "Student may request a review if within 5 credits of graduation and has extenuating circumstances",
            "approval_rules": {"max_shortfall": 5, "review_required": True, "always_denied": True},
        },
        {
            "exception_id": "EXC-009",
            "type": "hostel_capacity_override",
            "eligibility_conditions": "Not available — room capacity limits are strict",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-010",
            "type": "exam_reschedule",
            "eligibility_conditions": "Exam reschedule allowed only when student has a documented conflict",
            "approval_rules": {"conflict_required": True},
        },
        {
            "exception_id": "EXC-011",
            "type": "scholarship_credit_waiver",
            "eligibility_conditions": "Not available — scholarship credit requirements are non-negotiable",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-012",
            "type": "cgpa_registration_waiver",
            "eligibility_conditions": "Not available — minimum CGPA for registration is not waivable",
            "approval_rules": {"always_denied": True},
        },
        {
            "exception_id": "EXC-013",
            "type": "late_fee_payment",
            "eligibility_conditions": "Late fee payment accepted with ₹500 late fee surcharge",
            "approval_rules": {"late_surcharge": 500},
        },
        {
            "exception_id": "EXC-014",
            "type": "academic_probation_clearance",
            "eligibility_conditions": "Probation may be cleared if CGPA has recovered to 6.0+ for current semester",
            "approval_rules": {"min_cgpa_recovery": 6.0},
        },
        {
            "exception_id": "EXC-015",
            "type": "hostel_checkout_extension",
            "eligibility_conditions": "Checkout deadline extension of 15 days available with department head approval",
            "approval_rules": {"max_extension_days": 15, "dept_head_approval": True},
        },
    ]
    world["exceptions"] = exceptions

    #  14. Notifications (10) ─
    notifications = [
        {
            "notification_id": "NTF-001",
            "type": "regulation_change",
            "content": "REGULATION UPDATE: For graduating students in their final semester, the credit limit has been temporarily raised from 21 to 24 credits. Effective immediately. Ref: REG-2024-TEMP-07",
            "trigger_condition": f"check_credit_limits called for {task5_student_id}",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-002",
            "type": "deadline_warning",
            "content": "WARNING: The add/drop deadline is approaching. Course modifications will be locked after the deadline.",
            "trigger_condition": "task_3 step >= 12",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-003",
            "type": "capacity_alert",
            "content": "ALERT: Course enrollment approaching capacity. Only limited seats remain.",
            "trigger_condition": "check_seat_availability returns <= 2 seats",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-004",
            "type": "fee_reminder",
            "content": "REMINDER: Outstanding fees must be cleared before any administrative action can proceed.",
            "trigger_condition": "check_fee_clearance returns outstanding > 0",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-005",
            "type": "scholarship_warning",
            "content": "WARNING: Dropping courses may affect your scholarship eligibility. Please verify credit requirements.",
            "trigger_condition": "drop_course called for scholarship beneficiary",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-006",
            "type": "probation_notice",
            "content": "NOTICE: This student is on academic probation. Special restrictions apply to enrollment changes.",
            "trigger_condition": "get_student_record returns academic_status=probation",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-007",
            "type": "hostel_deadline",
            "content": "NOTICE: Hostel checkout deadline is April 30, 2025. Graduating students must initiate checkout.",
            "trigger_condition": "get_hostel_details called for graduating student",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-008",
            "type": "exam_conflict",
            "content": "ALERT: Exam schedule conflict detected. Two exams are scheduled at the same time.",
            "trigger_condition": "get_exam_schedule returns conflicting entries",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-009",
            "type": "system_info",
            "content": "INFO: All administrative changes are logged in the audit trail for compliance purposes.",
            "trigger_condition": "first modify tool called",
            "target_audience": "agent",
        },
        {
            "notification_id": "NTF-010",
            "type": "graduation_checklist",
            "content": "CHECKLIST: Graduation eligibility requires: (1) 160+ credits, (2) fee clearance, (3) no academic holds, (4) hostel checkout initiated, (5) all course requirements met.",
            "trigger_condition": "submit_final_response for task_5",
            "target_audience": "agent",
        },
    ]
    world["notifications"] = notifications

    #  15. Audit Log (empty — grows during episode) ─
    world["audit_log"] = []

    #  Competitive hard-task repairs 
    # Task 5: ensure Karthik is NOT already enrolled in the capstone and
    # requires both a waiver and the temporary credit-limit increase.
    task5_capstone_id = cs_courses[5]["course_id"] if len(cs_courses) > 5 else None
    task5_prereq_id = cs_courses[6]["course_id"] if len(cs_courses) > 6 else None
    task5_equivalent_id = cs_courses[7]["course_id"] if len(cs_courses) > 7 else None
    task5_anchor_courses = [c["course_id"] for c in cs_courses[:6]]

    if task5_capstone_id and task5_prereq_id and task5_equivalent_id:
        for course in courses:
            if course["course_id"] == task5_capstone_id:
                course["prerequisites"] = [task5_prereq_id]
                course["credits"] = 3
                course["semester_offered"] = 8
            elif course["course_id"] == task5_prereq_id:
                course["credits"] = 3
            elif course["course_id"] == task5_equivalent_id:
                course["credits"] = 3

        for course_id, credits in zip(task5_anchor_courses[:5], [4, 4, 4, 3, 3]):
            for course in courses:
                if course["course_id"] == course_id:
                    course["credits"] = credits
                    break

        world["enrollments"] = [
            e for e in world["enrollments"]
            if e["student_id"] != task5_student_id
        ]
        replacement_enrollments = []
        for idx, course_id in enumerate(task5_anchor_courses[:5], start=1):
            replacement_enrollments.append({
                "enrollment_id": f"ENR-T5-{idx:03d}",
                "student_id": task5_student_id,
                "course_id": course_id,
                "semester": 8,
                "grade": None,
                "status": "enrolled",
            })
        replacement_enrollments.append({
            "enrollment_id": "ENR-T5-900",
            "student_id": task5_student_id,
            "course_id": task5_equivalent_id,
            "semester": 7,
            "grade": "B+",
            "status": "completed",
        })
        world["enrollments"].extend(replacement_enrollments)

        for course in courses:
            active_count = sum(
                1 for e in world["enrollments"]
                if e["course_id"] == course["course_id"] and e["status"] == "enrolled"
            )
            course["current_enrollment"] = max(active_count, min(course["current_enrollment"], course["max_capacity"] - 1))

        for student in students:
            if student["student_id"] == task5_student_id:
                student["credits_completed"] = 157
                student["academic_status"] = "probation"
                break

    #  Store task-specific entity references 
    # This metadata helps task definitions reference the right entities
    world["_task_entity_refs"] = {
        "task_1": {
            "student_id": task1_student_id,
            "current_courses": student_current_enrollments.get(task1_student_id, []),
            "target_semester": 6,
        },
        "task_2": {
            "student_id": task2_student_id,
            "available_female_room": "RM-E001",
        },
        "task_3": {
            "student_id": task3_student_id,
            "course_a_id": task3_course_a_id,
            "course_b_id": task3_course_b_id,
            "scholarship_id": "SCH-001",
        },
        "task_4": {
            "student_x_id": task4_student_x_id,
            "student_y_id": task4_student_y_id,
            "course_id": task4_course_id,
            "scholarship_id": "SCH-002",
        },
        "task_5": {
            "student_id": task5_student_id,
            "student_name": "Karthik Nair",
            "capstone_course_id": task5_capstone_id,
            "prerequisite_course_id": task5_prereq_id,
            "equivalent_course_id": task5_equivalent_id,
            "elective_course_id": cs_courses[8]["course_id"] if len(cs_courses) > 8 else None,
            "scholarship_id": "SCH-003",
            "blockers": [
                "missing_credits",
                "unpaid_fees",
                "missing_prerequisite",
                "scholarship_min_credits",
                "hostel_checkout",
                "academic_probation_flag",
            ],
        },
        "task_6": {
            "student_conflict_pairs": task6_course_pairs,
        },
    }

    return world


def generate_policies() -> Dict[str, Any]:
    """Generate the university policies document.

    Returns a dict of policy categories with their rules.
    """
    return {
        "enrollment_policies": {
            "max_credits_per_semester": 21,
            "elevated_credit_limit_graduating": 24,
            "prerequisite_enforcement": True,
            "prerequisite_waiver_min_grade": "B",
            "fee_clearance_required": True,
            "min_cgpa_for_registration": 4.0,
            "duplicate_enrollment_blocked": True,
            "capacity_strictly_enforced": True,
        },
        "hostel_policies": {
            "gender_restriction_enforced": True,
            "max_room_capacity": 2,
            "fee_clearance_for_allocation": True,
            "checkout_deadline_graduating": "2025-04-30",
            "transfer_requires_fee_clearance": True,
        },
        "fee_policies": {
            "partial_payments_accepted": True,
            "outstanding_fees_block_enrollment": True,
            "outstanding_fees_block_hostel": True,
            "late_payment_surcharge": 500,
            "deferral_requires_scholarship_50pct": True,
        },
        "scholarship_policies": {
            "min_credit_maintenance_required": True,
            "course_dependency_priority_over_cgpa": True,
            "non_compliance_triggers_review": True,
        },
        "exam_policies": {
            "no_same_day_exams_per_student": True,
            "no_double_booking_rooms": True,
            "faculty_single_slot_invigilation": True,
            "department_resolves_conflicts": True,
        },
        "academic_policies": {
            "graduation_min_credits": 160,
            "probation_credit_limit": 15,
            "probation_clearance_cgpa": 6.0,
            "probation_clearance_consecutive_semesters": 2,
            "withdrawal_grade": "W",
        },
        "exception_rules": {
            "credit_overload": "Approved ONLY IF final semester AND ≤3 credits short of 160",
            "prerequisite_waiver": "Approved ONLY IF equivalent course completed with grade ≥ B",
            "fee_deferral": "Approved ONLY IF active scholarship covers ≥50% of fees",
            "all_others": "DENIED by default",
        },
    }


def main() -> None:
    """Generate and save the world seed and policies."""
    output_dir = os.path.join(os.path.dirname(__file__))

    # Generate world
    world = generate_world()

    # Save world_seed.json
    world_path = os.path.join(output_dir, "world_seed.json")
    with open(world_path, "w", encoding="utf-8") as f:
        json.dump(world, f, indent=2, sort_keys=False, ensure_ascii=False)

    # Generate and save policies
    policies = generate_policies()
    policies_path = os.path.join(output_dir, "policies.json")
    with open(policies_path, "w", encoding="utf-8") as f:
        json.dump(policies, f, indent=2, sort_keys=False, ensure_ascii=False)

    # Print summary
    entity_counts = {
        "students": len(world["students"]),
        "courses": len(world["courses"]),
        "faculty": len(world["faculty"]),
        "departments": len(world["departments"]),
        "enrollments": len(world["enrollments"]),
        "hostel_blocks": len(world["hostel_blocks"]),
        "hostel_rooms": len(world["hostel_rooms"]),
        "fee_records": len(world["fee_records"]),
        "scholarships": len(world["scholarships"]),
        "exam_schedule": len(world["exam_schedule"]),
        "regulations": len(world["regulations"]),
        "exceptions": len(world["exceptions"]),
        "notifications": len(world["notifications"]),
        "audit_log": len(world["audit_log"]),
    }

    total = sum(entity_counts.values())
    print("World generated successfully.")
    print(f"   Output: {world_path}")
    print(f"   Policies: {policies_path}")
    print(f"\n   Entity counts:")
    for etype, count in entity_counts.items():
        print(f"     {etype}: {count}")
    print(f"\n   Total entities: {total}")

    # Verify task-specific entities
    refs = world["_task_entity_refs"]
    print(f"\n   Task entity references:")
    for task_name, task_refs in refs.items():
        print(f"     {task_name}: {list(task_refs.keys())}")

    # Determinism check
    world2 = generate_world()
    world_json_1 = json.dumps(world, sort_keys=True)
    world_json_2 = json.dumps(world2, sort_keys=True)
    if world_json_1 == world_json_2:
        print("\n   Determinism verified: two generations produce identical output")
    else:
        print("\n   DETERMINISM FAILURE: two generations differ!")


if __name__ == "__main__":
    main()
