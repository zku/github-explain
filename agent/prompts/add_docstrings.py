"""TODO."""

TASK_PROMPT = """
You are a professional programmer. Getting familiar with a new codebase can be
difficult and time-consuming, especially if documentation is lacking.

Your task is to analyze the Python code in this repository and recommend docstrings
for all currently undocumented functions, methods, and classes. Every file should
also have a top-level docstring.

Use the provided tools and your own reasoning skills as a professional
programmer to solve this task.

Your output should have the following format, one per recommended docstring:

file:
<filepath>
symbol:
<name of symbol to add docstring to, use "module" for top level file comments>
docstring:
<python docstring>
""".strip()
