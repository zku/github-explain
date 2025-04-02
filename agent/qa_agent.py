"""TODO."""

from rich.prompt import Prompt

from .agent import CodeAnalysisAgent


async def qa_agent(code_analysis_agent: CodeAnalysisAgent, start_prompt) -> None:
    """Runs the code analysis agent to ask questions about the code."""
    await code_analysis_agent.run(start_prompt)
    while True:
        user_question = Prompt.ask("USER >> ")
        await code_analysis_agent._step(user_question)
