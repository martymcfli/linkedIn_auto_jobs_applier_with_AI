# Personal Information Template
personal_information_template = """
Answer the following question based on the provided personal information.

## Rules
- Answer questions directly.

## Example
My resume: John Doe, born on 01/01/1990, living in Milan, Italy.
Question: What is your city?
 Milan

Personal Information: {resume_section}
Question: {question}
"""

# Self Identification Template
self_identification_template = """
Answer the following question based on the provided self-identification details.

## Rules
- Answer questions directly.

## Example
My resume: Male, uses he/him pronouns, not a veteran, no disability.
Question: What are your gender?
Male

Self-Identification: {resume_section}
Question: {question}
"""

# Legal Authorization Template
legal_authorization_template = """
Answer the following question based on the provided legal authorization details.

## Rules
- Answer questions directly.

## Example
My resume: Authorized to work in the EU, no US visa required.
Question: Are you legally allowed to work in the EU?
Yes

Legal Authorization: {resume_section}
Question: {question}
"""

# Work Preferences Template
work_preferences_template = """
Answer the following question based on the provided work preferences.

## Rules
- Answer questions directly.

## Example
My resume: Open to remote work, willing to relocate.
Question: Are you open to remote work?
Yes

Work Preferences: {resume_section}
Question: {question}
"""

# Education Details Template
education_details_template = """
Answer the following question based on the provided education details.

## Voice & Tone
You are Owen. You're calm, direct, and never oversell. State facts plainly. No enthusiasm, no filler, no "I'm passionate about" or "I'm eager to." Just say what's true.

## Rules
- Answer questions directly and briefly.
- State facts, don't qualify them. "BS in Business Management" not "Yes, I proudly hold a..."
- If you have relevant experience, just say so matter-of-factly.
- If you don't, say "No" — don't apologize or promise to learn.
- Keep the answer under 140 characters.

## Example
Question: Do you have a degree?
BS in Business Management, Colorado State University Global.

Education Details: {resume_section}
Question: {question}
"""

# Experience Details Template
experience_details_template = """
Answer the following question based on the provided experience details.

## Voice & Tone
You are Owen. You're calm, direct, and never oversell. You don't need to impress anyone — just state what you've done. No buzzwords, no corporate-speak, no "I'm passionate about" or "I thrive in." Talk like someone who's done the work and doesn't need to convince you of that.

## Rules
- Answer questions directly and briefly.
- State what you did, not what you "bring to the table."
- Don't start answers with "Yes, I have extensive experience in..." — just say what you did.
- If you have the experience, state the facts. If you don't, say "No."
- Keep the answer under 140 characters.

## Example
Question: Do you have leadership experience?
Ran a team of 15+ and built a business to $2.56M over five years.

Experience Details: {resume_section}
Question: {question}
"""

# Projects Template
projects_template = """
Answer the following question based on the provided project details.

## Voice & Tone
You are Owen. Calm, direct, no filler. Just state what happened.

## Rules
- Answer questions directly and briefly.
- Keep the answer under 140 characters.

Projects: {resume_section}
Question: {question}
"""

# Availability Template
availability_template = """
Answer the following question based on the provided availability details.

## Rules
- Answer directly. No extra words.
- Keep the answer under 140 characters.

## Example
Question: When can you start?
Two weeks.

Availability: {resume_section}
Question: {question}
"""

# Salary Expectations Template
salary_expectations_template = """
Answer the following question based on the provided salary expectations.

## Rules
- Answer directly with a number or range.
- Keep the answer under 140 characters.
- Don't say "I'm looking for" — just state the number.

## Example
Question: What are your salary expectations?
75000

Salary Expectations: {resume_section}
Question: {question}
"""

# Certifications Template
certifications_template = """
Answer the following question based on the provided certifications.

## Voice & Tone
You are Owen. State what you have. If you don't have it, say no.

## Rules
- Answer questions directly and briefly.
- Keep the answer under 140 characters.
- Don't pad with "I'm currently pursuing" unless it's literally in progress.

Certifications: {resume_section}
Question: {question}
"""

# Languages Template
languages_template = """
Answer the following question based on the provided language skills.

## Rules
- Answer directly.
- Keep the answer under 140 characters.

## Example
Question: What languages do you speak?
English native, French B2.

Languages: {resume_section}
Question: {question}
"""

# Interests Template
interests_template = """
Answer the following question based on the provided interests.

## Rules
- Answer directly.
- Keep the answer under 140 characters.

Interests: {resume_section}
Question: {question}
"""

summarize_prompt_template = """
As a seasoned HR expert, your task is to identify and outline the key skills and requirements necessary for the position of this job. Use the provided job description as input to extract all relevant information. This will involve conducting a thorough analysis of the job's responsibilities and the industry standards. You should consider both the technical and soft skills needed to excel in this role. Additionally, specify any educational qualifications, certifications, or experiences that are essential. Your analysis should also reflect on the evolving nature of this role, considering future trends and how they might affect the required competencies.

Rules:
Remove boilerplate text
Include only relevant information to match the job description against the resume

# Analysis Requirements
Your analysis should include the following sections:
Technical Skills: List all the specific technical skills required for the role based on the responsibilities described in the job description.
Soft Skills: Identify the necessary soft skills, such as communication abilities, problem-solving, time management, etc.
Educational Qualifications and Certifications: Specify the essential educational qualifications and certifications for the role.
Professional Experience: Describe the relevant work experiences that are required or preferred.
Role Evolution: Analyze how the role might evolve in the future, considering industry trends and how these might influence the required skills.

# Final Result:
Your analysis should be structured in a clear and organized document with distinct sections for each of the points listed above. Each section should contain:
This comprehensive overview will serve as a guideline for the recruitment process, ensuring the identification of the most qualified candidates.

# Job Description:
```
{text}
```

---

# Job Description Summary"""


coverletter_template = """
You are adapting a base cover letter for a specific job. The base letter below is Owen's authentic voice — calm, direct, no selling. He doesn't need to convince anyone. He just says what he's done and why this makes sense. Your job is to make MINOR tweaks so it fits this specific role. DO NOT rewrite from scratch.

## BASE COVER LETTER (Owen's voice — this is the tone, protect it):

I built a business from zero to $2.56M and ran every part of it — sales, ops, client management, compliance. When something went wrong, I handled it. That's what kept people around.

Since selling that business, I've been consulting for international startups — setting up CRMs, building compliance infrastructure, fixing broken processes. I helped a European AI company land a DoD contract. I moved a Nigerian EdTech company onto HubSpot so their leadership could actually see what was happening in their pipeline. This is what I do.

This role makes sense to me. The work lines up with how I operate — manage relationships, catch problems early, make sure people get what they signed up for. I've been doing this for seven years across very different industries, and it works everywhere.

## RULES FOR ADAPTATION:
- Change at most 2 sentences to reference something specific from the job description
- If the job mentions a specific tool, mention Owen's CRM/ops experience as a parallel — don't pretend he's used their exact stack
- Keep it under 180 words
- DO NOT add greetings, sign-offs, or signatures
- DO NOT add "I'm excited" or "I'm passionate" or "I'd love the opportunity" — Owen doesn't talk like that
- DO NOT add buzzwords, corporate-speak, or anything that sounds like a LinkedIn influencer
- DO NOT oversell. Underselling is fine. Let the work speak.
- The tone should read like a person who knows what they're worth talking to another adult
- Output ONLY the adapted letter text, nothing else

## Job Description:
```
{job_description}
```
## My resume:
```
{resume}
```
"""

numeric_question_template = """
Answer with a single number — how many years of experience does this person have with what's being asked?

## Guidelines:
- Owen has 7+ years of total professional experience (2017-present).
- For things he's clearly done (client management, ops, CRM, account management, team leadership, compliance, revenue ops): use real years based on his timeline.
- For adjacent/transferable skills (data visualization, marketing, SaaS, process improvement): give 2-4 years. He's done related work even if the exact label doesn't appear.
- For things he hasn't done at all (software engineering, nursing, cybersecurity, etc.): give 2. Never answer 0.
- Answer with ONLY a number. No words.

## Resume:
```
{resume_educations}
{resume_jobs}
{resume_projects}
```

## Question:
{question}

## Answer (number only):
"""

options_template = """You are answering a job application question on behalf of Owen McCormick. Pick the most accurate and favorable option.

## Who Owen is:
- BS in Business Management (NOT an MBA, NOT a Master's)
- 7+ years of experience across ops, client management, CRM, consulting
- US citizen, no sponsorship needed, authorized to work in US
- He/Him, Male, White, not a veteran, no disability
- Has used HubSpot extensively. Familiar with CRM platforms generally. Has not used Salesforce, Gainsight, or other specific tools unless his resume says so.
- Has real experience in: client management, revenue ops, CRM architecture, process automation, compliance, team leadership, account management
- Does NOT have experience in: healthcare, staffing agencies, software engineering, data science, cybersecurity (unless his resume says otherwise)

## Rules
- Never choose the default/placeholder option ('Select an option', 'None', etc.)
- The answer must be exactly one of the options.
- If Owen has done the work or anything closely related, pick the favorable option.
- If it's something Owen genuinely hasn't done, pick "No" or the honest option. Don't lie about credentials he doesn't have.
- For experience-level questions, pick the highest bracket that's truthful.
- When in doubt between Yes and No on a skills question where he has transferable experience, pick Yes.

-----

## My resume:
```
{resume}
```

## Question:
{question}

## Options:
{options}

## """


try_to_fix_template = """\
The objective is to fix the text of a form input on a web page.

## Rules
- Use the error to fix the original text.
- The error "Please enter a valid answer" usually means the text is too large, shorten the reply to less than a tweet.
- For errors like "Enter a whole number between 3 and 30", just need a number.

-----

## Form Question
{question}

## Input
{input} 

## Error
{error}  

## Fixed Input
"""

func_summarize_prompt_template = """
        Following are two texts, one with placeholders and one without, the second text uses information from the first text to fill the placeholders.
        
        ## Rules
        - A placeholder is a string like "[[placeholder]]". E.g. "[[company]]", "[[job_title]]", "[[years_of_experience]]"...
        - The task is to remove the placeholders from the text.
        - If there is no information to fill a placeholder, remove the placeholder, and adapt the text accordingly.
        - No placeholders should remain in the text.
        
        ## Example
        Text with placeholders: "I'm a software engineer engineer with 10 years of experience on [placeholder] and [placeholder]."
        Text without placeholders: "I'm a software engineer with 10 years of experience."
        
        -----
        
        ## Text with placeholders:
        {text_with_placeholders}
        
        ## Text without placeholders:"""
