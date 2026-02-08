"""
Job Hunter Agent — Automates job search and application pipeline.
Tailored for: Data Analyst, Data Scientist, AI Engineer, PM roles
Target: AI startups, big tech, fintech in NYC ($150k-180k)
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from loguru import logger

from shared.base_agent import BaseAgent
from shared.llm import TaskComplexity


class JobHunterAgent(BaseAgent):
    name = "job_hunter"
    description = "Searches for jobs, matches against preferences, and auto-applies"
    schedule = "every 6 hours"

    def get_tools(self) -> list:
        prefs = self.config.get("preferences", {})

        @tool
        def search_job_boards(query: str) -> str:
            """Search job boards for matching positions. Returns list of job postings."""
            # TODO: Implement with Playwright browser automation
            # Scrape LinkedIn, Wellfound, Greenhouse, Lever
            return f"[Placeholder] Searched for: {query}. Would scrape job boards here."

        @tool
        def analyze_job_fit(job_description: str) -> str:
            """Analyze how well a job matches the user's profile and preferences."""
            target_roles = prefs.get("target_roles", [])
            skills = prefs.get("skills", [])
            salary_min = prefs.get("salary_min", 0)

            return (
                f"[Placeholder] Would analyze job against:\n"
                f"Target roles: {target_roles}\n"
                f"Skills: {skills}\n"
                f"Min salary: ${salary_min:,}"
            )

        @tool
        def generate_cover_letter(job_title: str, company: str, job_description: str) -> str:
            """Generate a tailored cover letter for a specific job."""
            return (
                f"[Placeholder] Would generate cover letter for {job_title} at {company}\n"
                f"Using Claude/GPT-4 for quality. Based on resume at: "
                f"{prefs.get('resume_path', 'not set')}"
            )

        @tool
        def submit_application(job_url: str, cover_letter: str) -> str:
            """Submit a job application. Requires approval if configured."""
            return f"[Placeholder] Would submit application to {job_url}"

        @tool
        def check_application_status(company: str) -> str:
            """Check status of previously submitted applications."""
            recent = self.recall(f"application {company}", n_results=5)
            if recent:
                return f"Found {len(recent)} past interactions with {company}"
            return f"No previous applications found for {company}"

        return [search_job_boards, analyze_job_fit, generate_cover_letter, submit_application, check_application_status]

    def get_system_prompt(self) -> str:
        prefs = self.config.get("preferences", {})
        return f"""You are the Job Hunter agent for Holus, a personal AI workforce system.

Your mission: Find and apply to the best job opportunities for the user.

USER PROFILE:
- Target roles: {', '.join(prefs.get('target_roles', ['Data Analyst', 'AI Engineer']))}
- Target companies: {', '.join(prefs.get('target_companies', ['AI startups', 'Big tech']))}
- Location: {prefs.get('location', 'New York City')}
- Salary range: ${prefs.get('salary_min', 150000):,} - ${prefs.get('salary_max', 180000):,}
- Key skills: {', '.join(prefs.get('skills', ['Python', 'SQL', 'ML']))}
- Bilingual: English/Spanish
- Education: MS in Data Analytics (current)

WORKFLOW:
1. Search job boards for matching positions
2. Analyze each job for fit (role match, salary, company type)
3. Filter to top candidates (score 7+/10)
4. For top matches: generate tailored cover letter
5. If require_approval is true, send summary to user for approval before applying
6. Track all applications in memory

RULES:
- Max {self.config.get('max_applications_per_day', 10)} applications per day
- Always check memory for previously applied companies (no duplicates)
- Prioritize: AI startups > fintech > big tech
- Flag any role that mentions visa sponsorship requirements
- Send daily summary via notification
"""

    async def run(self) -> dict[str, Any]:
        """Execute the job hunting pipeline."""
        logger.info("🎯 Job Hunter starting search...")

        # Check what we've done recently
        recent_apps = self.recall("application submitted", n_results=20)
        applied_count_today = len([
            r for r in recent_apps
            if "today" in r.get("metadata", {}).get("timestamp", "")
        ])

        max_daily = self.config.get("max_applications_per_day", 10)
        remaining = max_daily - applied_count_today

        if remaining <= 0:
            msg = f"Daily application limit reached ({max_daily}). Skipping this run."
            logger.info(msg)
            return {"status": "skipped", "reason": "daily_limit"}

        # Run the search pipeline
        result = await self.execute(
            f"Search for the latest job openings matching my profile. "
            f"Focus on roles posted in the last 24 hours. "
            f"I have {remaining} application slots remaining today. "
            f"Find the best matches, analyze fit, and prepare applications.",
            complexity=TaskComplexity.COMPLEX,
        )

        # Notify user with summary
        await self.notify(
            f"🎯 *Job Hunt Complete*\n\n{result[:500]}"
        )

        self.remember(
            f"Job hunt run completed. Result: {result[:300]}",
            metadata={"type": "run_summary"},
        )

        return {"status": "completed", "result": result}
