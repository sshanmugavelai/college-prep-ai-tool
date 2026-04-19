QUESTION_GENERATION_PROMPT = """
You are an SAT/ACT question writer and tutor.
Generate original {exam_type} {section} questions.

Requirements:
- Number of questions: {num_questions}
- Difficulty: {difficulty}
- Avoid copyrighted passages; keep content original.
- Use clear language for a high school student.
- Each question must have exactly 4 choices.
- correct_answer must be one of: A, B, C, D.
- topic should be a concise skill tag like algebra, grammar, inference, punctuation.
- explanation should be 2-4 sentences.

Return ONLY valid JSON in this exact schema:
{{
  "questions": [
    {{
      "question": "...",
      "choices": ["...", "...", "...", "..."],
      "correct_answer": "B",
      "explanation": "...",
      "topic": "algebra",
      "difficulty": "{difficulty}"
    }}
  ]
}}
"""


MISTAKE_EXPLANATION_PROMPT = """
You are a patient SAT/ACT tutor. Analyze one question attempt.

Exam: {exam_type}
Section: {section}
Question: {question}
Choices: {choices}
Correct answer: {correct_answer}
User answer: {user_answer}
Topic: {topic}
Difficulty: {difficulty}

Return ONLY valid JSON in this exact schema:
{{
  "correct_explanation": "...",
  "why_user_wrong": "...",
  "concept_to_learn": "...",
  "difficulty_adjustment": "increase/decrease/same"
}}
"""


REVIEW_HINTS_PROMPT = """
You are a patient SAT/ACT tutor. The student already submitted this question — they may have been correct,
used a longer path, or picked a wrong answer for an interesting reason. They are reviewing on flashcards
or with hints (not re-taking the test).

Exam: {exam_type}
Section: {section}
Topic: {topic}
Difficulty: {difficulty}
Question: {question}
Choices (A–D): {choices_lines}
The student's answer was: {user_answer}
The correct answer is: {correct_answer} (use this only to shape hints; do not leak the letter in hints 1–2.)

Write exactly 3 short hints for spaced review, from gentle → more specific:
- Hint 1: skill or reading strategy to try first (no letters).
- Hint 2: a nudge about comparing choices or checking evidence (no correct letter).
- Hint 3: may narrow the reasoning but still keep it study-focused (avoid spoiling the click if possible).

Return ONLY valid JSON:
{{
  "hints": ["...", "...", "..."]
}}
"""


STUDY_PLAN_PROMPT = """
You are an SAT/ACT prep coach.
Generate a 7-day study plan based on the student performance data.

Performance summary:
{performance_summary}

Rules:
- Keep plan realistic for a student.
- Include specific topics, daily question counts, and schedule hints.
- Focus extra time on weak topics.

Return ONLY valid JSON in this schema:
{{
  "weekly_plan": [
    {{
      "day": "Monday",
      "focus_topics": ["..."],
      "questions_target": 20,
      "schedule_tip": "..."
    }}
  ],
  "overall_advice": "..."
}}
"""
