"""TODO."""

TASK_PROMPT = """
# Task
You are a professional programmer. Getting familiar with a new codebase can be
difficult and time-consuming.

Your task is to analyze the code in this repository and to provide a reference
manual so that someone else can easily understand the architecture of the
project. Your reference manual should describe the high-level architecture and
serve as a guide on getting familiar with the codebase.

Use the provided tools and your own reasoning skills as a professional
programmer to solve this task.

# Guidelines
- Before you provide a reference manual, you should inspect all relevant files.
- Do not base your review solely on the directory structure.
- Do not base your review solely on any README or wiki files.
- Your review must include source code.
- Use your own critical thinking as necessary.
- Use the available tools as necessary.
- If the project contains many files, try to start with obvious entry points.
- You must analyze at least 15 source code files (if there are 15 or more).

On task completion, use the finish tool to provide your result.
""".strip()
