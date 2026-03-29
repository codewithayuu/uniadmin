---
title: UniAdmin v1.0
emoji: "🏛️"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
tags:
  - openenv
---

# 🏛️ UniAdmin v1.0

**University Administrative Operations Environment for Agentic RL**

A fully simulated university administrative operations environment built on the [OpenEnv](https://github.com/openenv) spec. An AI agent acts as a university admin desk officer processing student requests across **~1,800 interconnected entities** using **26 tools** and **6 graded tasks** with difficulty ranging from easy to genuinely hard for frontier models.

---

## 🏗️ Architecture

```
┌─────────────────┐     HTTP      ┌──────────────────────────────────┐
│  inference.py   │◄────────────►│  FastAPI Server (port 7860)       │
│  (OpenAI LLM)   │              │                                    │
│                  │  POST /reset │  ┌──────────────────────────────┐ │
│  UniAdminClient  │  POST /step  │  │  UniAdminEnvironment          │ │
│                  │  GET /state  │  │                                │ │
└─────────────────┘  GET /tasks  │  │  Entity Graph (~4,000)        │ │
                     GET /grader  │  │  21 Tool Handlers              │ │
                     GET /health  │  │  6 Rubric Graders              │ │
                                  │  │  Audit Log + Notifications     │ │
                                  │  └──────────────────────────────┘ │
                                  └──────────────────────────────────┘
```

**Flow:** `reset(task_id)` → agent calls tools via `step(action)` → environment returns observations with rewards → agent calls `submit_final_response` → grader evaluates rubric → final score returned.

---

## 🎯 Why This Domain

University administration is **absent from ALL existing agent benchmarks** (τ-bench, CoreCraft, WebArena, etc.). It involves:

- **Multi-step reasoning** — checking prerequisites, fees, schedules before acting
- **Policy compliance** — regulations that constrain valid actions
- **Multi-entity coordination** — students, courses, hostels, scholarships interlinked
- **Hidden information** — blockers that must be discovered through investigation
- **Time pressure** — deadlines that invalidate actions mid-episode

This creates a rich, realistic environment where an agent must plan, discover, validate, and act — skills that simple benchmarks cannot test.

---

## 📊 Entity Graph (~4,000 Entities, 14 Types)

| Entity Type | Count | Key Fields |
|---|---|---|
| Students | 400 | student_id, name, department, semester, cgpa, academic_status |
| Courses | 120 | course_id, name, credits, prerequisites, capacity, enrollment |
| Faculty | 60 | faculty_id, name, department, courses_teaching |
| Departments | 12 | dept_id, name, head_of_dept, courses_offered |
| Enrollments | ~2000 | enrollment_id, student_id, course_id, grade, status |
| Hostel Blocks | 8 | block_id, capacity, gender_restriction |
| Hostel Rooms | ~400 | room_id, block_id, capacity, current_occupants |
| Fee Records | 400 | student_id, amount_due, amount_paid, status |
| Scholarships | 30 | scholarship_id, criteria, min_cgpa, beneficiaries |
| Exam Schedule | ~200 | exam_id, course_id, date, time_slot, room |
| Regulations | 25 | reg_id, title, conditions |
| Exceptions | 15 | exception_id, type, approval_rules |
| Notifications | 10 | notification_id, trigger_condition |
| Audit Log | 0→∞ | grows during episode |

**Total: ~3,700 entities** — every entity is reachable from at least one task.

---

## 🔧 Tool Catalog (21 Tools)

| # | Category | Tool | Mutates State |
|---|---|---|---|
| 1-5 | **Search** | search_students, search_courses, search_faculty, search_regulations, search_scholarships | No |
| 6-11 | **Retrieve** | get_student_record, get_course_details, get_enrollment_history, get_fee_status, get_hostel_details, get_exam_schedule | No |
| 12-16 | **Validate** | check_prerequisites, check_credit_limits, check_seat_availability, check_fee_clearance, check_scholarship_compliance | No |
| 17-20 | **Modify** | enroll_student, drop_course, transfer_hostel, update_fee_record | **Yes** |
| 21 | **Special** | submit_final_response (terminal action) | No |

---

## 📋 Tasks & Difficulty Curve

| Task | Difficulty | Max Steps | Description | GPT-4o Expected |
|---|---|---|---|---|
| Task 1: Course Inquiry | Easy | 15 | Find available CS electives without conflicts | 0.85-0.95 |
| Task 2: Hostel Allocation | Easy | 15 | Allocate gender-appropriate room with fee check | 0.80-0.90 |
| Task 3: Course Switch | Medium | 20 | Switch courses before deadline (step 16) | 0.50-0.70 |
| Task 4: Concurrent Conflict | Medium | 25 | Two students competing for last seat (policy priority) | 0.40-0.60 |
| Task 5: Graduation Crisis | **Hard** | 40 | 6 hidden blockers + dynamic regulation change | **0.05-0.20** |
| Task 6: Bulk Schedule | **Hard** | 50 | Resolve 8 exam conflicts (constraint satisfaction) | **0.05-0.15** |

---

## 🔬 Worked Example: Task 5 — The "Mic Drop"

**Scenario:** Final-semester student "Karthik" (STU-042) requests a graduation eligibility check. He *appears* fine on the surface.

**What the agent must discover through investigation:**

| # | Blocker | How to Discover | How to Resolve |
|---|---|---|---|
| 1 | Missing 2 credits | `check_credit_limits` → headroom is negative | Dynamic regulation raises limit from 21→24 (triggered by the credit check!) |
| 2 | ₹2,500 unpaid fees | `get_fee_status` → amount_due=2500 | `update_fee_record` with payment_amount=2500 |
| 3 | Missing capstone prerequisite | `check_prerequisites` → missing Software Engineering | `enroll_student` with exception_override=true (has equivalent course with B+) |
| 4 | Scholarship min-credit violation | `check_scholarship_compliance` → below minimum | Resolved by NOT dropping courses (careful planning) |
| 5 | Hostel checkout not initiated | `get_hostel_details` → checkout_initiated=false | Note in resolution summary |
| 6 | Academic probation flag | `get_student_record` → academic_status=probation | CGPA is 7.50 (≥6.0) → clearable |

**The dynamic regulation twist:** When the agent calls `check_credit_limits` for Karthik, a notification fires:

> *"REGULATION UPDATE: For graduating students in their final semester, the credit limit has been temporarily raised from 21 to 24 credits."*

If the agent never checks credit limits, it never discovers this — and must find another way to resolve the credit gap.

**Why GPT-4o scores < 0.20:** It typically discovers 2-3 blockers, resolves 1, and misses the dynamic regulation entirely. The interconnected nature of the blockers (can't enroll without paying fees, can't drop courses without breaking scholarship) requires global planning that current models struggle with.

---

## 🚀 Quick Start

### Docker (recommended)

```bash
docker build -t uniadmin .
docker run -p 7860:7860 uniadmin

# Health check
curl http://localhost:7860/health

# List tasks
curl http://localhost:7860/tasks
```

### Local

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e .
python uniadmin/world/generator.py

# Start server
uvicorn uniadmin.server.app:app --host 0.0.0.0 --port 7860

# Run inference (in another terminal)
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your_key"
python inference.py
```

### Validate

```bash
# Run test suite
python -m pytest uniadmin/tests/ -v

# Verify determinism
python -c "
from uniadmin.server.uniadmin_environment import UniAdminEnvironment
env = UniAdminEnvironment()
env.reset(); h1 = env.state().state_hash
env.reset(); h2 = env.state().state_hash
assert h1 == h2; print('Deterministic ✅')
env.close()
"
```

---

## 🏆 Novel Mechanics

1. **Mid-episode dynamic regulation change** — agent must adapt plan when rules change
2. **Deadline-based action invalidation** — modify tools stop working after step N
3. **Multi-party conflict resolution** — two students competing for one seat
4. **Hidden blocker discovery** — information not given upfront, must be found
5. **Cascading constraint satisfaction** — resolving one conflict may create another
6. **Policy-before-priority reasoning** — scholarship dependency > CGPA ordering

---

## 📁 Project Structure

```
uniadmin/
├── __init__.py              # Package exports
├── models.py                # Pydantic Action/Observation/State + 21 tool schemas
├── client.py                # HTTP client for the environment
├── world/
│   ├── generator.py         # Deterministic entity graph generator (seed=42)
│   ├── loader.py            # Deep-copy world loader
│   ├── world_seed.json      # Generated entity graph
│   └── policies.json        # University regulations
├── tasks/                   # Task definition JSONs (6 tasks)
├── graders/
│   ├── base_grader.py       # Shared rubric evaluation utilities
│   ├── dispatcher.py        # Routes task_id → grader function
│   └── grader_task_[1-6].py # Deterministic rubric graders
├── server/
│   ├── uniadmin_environment.py  # Core environment (21 tools)
│   └── app.py               # FastAPI HTTP server
├── tests/                   # Test suite
├── openenv.yaml             # OpenEnv manifest
├── Dockerfile               # Container definition
├── requirements.txt         # Dependencies
├── inference.py             # Baseline inference script (root)
└── README.md                # This file
```

---

## 📄 License

MIT
