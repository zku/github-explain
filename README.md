Implements AI agents using Google's Gemini models with tool-calling support via MCP or in-process functions.

The following contents are AI generated using the agent's `project_analysis` task.

## Codebase Reference Manual

This document provides a high-level overview of the codebase and serves as a guide for understanding
the project's architecture.

### 1. Project Description

The project appears to be a code analysis agent that uses Google's Gemini AI model to analyze a
codebase. It leverages the `mcp` (Modular Code Platform) library for interacting with external tools
and the `genai` library for interacting with the Gemini model. The agent aims to automate code
understanding and potentially code modification tasks.

### 2. High-Level Architecture

The project consists of the following main components:

*   **`main.py`**: This is the entry point of the application. It initializes the Gemini client and
the MCP client (a dummy tool server for now). It then creates a `CodeAnalysisAgent` and starts the
analysis process by providing an initial task prompt.
*   **`agent/agent.py`**: This file contains the core logic of the `CodeAnalysisAgent`. The agent
interacts with the Gemini model, manages the conversation history, calls tools through the MCP
client, and presents the results to the user. The agent operates in a loop, prompting the model,
processing the response (which may include tool calls), and updating the conversation history.
*   **`agent/tools/dummy_tool.py`**: This is a dummy implementation of a tool server using the MCP
library. It provides two tools: `list_files` (lists files in the project) and `read_file` (reads the
content of a file). This is a simple, file-system based tool and will likely be replaced with a more
sophisticated tool that interacts with the cloned GitHub project.
*   **`agent/prompts/`**: This directory contains prompt files used by the agent.
`project_analysis.py` likely contains the initial task prompt given to the agent.

### 3. Key Components and Their Functionality

*   **`CodeAnalysisAgent`**:
    *   Takes a `genai.Client` and a list of `ClientSession` (MCP clients) as input.
    *   `run(task_prompt)`: Starts the agent loop with an initial task prompt.
    *   `_step(prompt)`: Performs one interaction step with the Gemini model:
        *   Adds the user prompt to the conversation history.
        *   Calls the Gemini model to generate a response.
        *   If the response contains function calls, calls the corresponding tools using the MCP
client and adds the results to the history.
    *   `_call_tool(name, args)`: Calls a specific tool through the MCP client. It asks the user for
permission before executing the tool.
*   **MCP (Modular Code Platform)**:
    *   Provides a framework for defining and calling tools.
    *   `dummy_tool.py` defines a simple MCP server with two tools: `list_files` and `read_file`.
    *   The agent interacts with these tools through `ClientSession`.
*   **Gemini API**:
    *   Used for interacting with the Gemini language model.
    *   The agent sends prompts and conversation history to the model.
    *   The model generates responses, which may include text and/or function calls.

### 4. Workflow

1.  The `main.py` script initializes the Gemini client and the MCP client (dummy tool server).
2.  It creates an instance of the `CodeAnalysisAgent`, passing in the Gemini client and MCP client.
3.  It calls the `run` method of the agent, providing an initial task prompt (from
`agent/prompts/project_analysis.py`).
4.  The `run` method enters a loop:
    *   The `_step` method is called, which sends the prompt to the Gemini model.
    *   The model generates a response.
    *   If the response contains function calls, the agent calls the corresponding tools using the
MCP client.
    *   The results of the tool calls are added back to the conversation history.
    *   The loop continues until the model no longer requests function calls.

### 5. Getting Started

To understand the codebase, start by examining the following files:

*   `main.py`: To understand the application's entry point and initialization process.
*   `agent/agent.py`: To understand the core logic of the code analysis agent.
*   `agent/tools/dummy_tool.py`: To understand how tools are defined and called using the MCP
library.
*   `agent/prompts/project_analysis.py`: To understand the initial task prompt given to the agent.

### 6. Future Development Areas

Based on the code and the "TODO" comments, here are potential future development areas:

*   **GitHub Project Cloning**: Implement the functionality to clone a GitHub project (without
submodules and with empty LFS filters) inside a Docker container.
*   **File Server**: Replace the dummy tool server with a read-only file server that serves files
from the cloned GitHub project.
*   **Tool Development**: Create more sophisticated tools for code analysis and modification.
*   **Error Handling**: Improve error handling and logging.
*   **Prompt Engineering**: Improve the prompts in `agent/prompts/` to guide the agent towards more
effective code analysis.
*   **Security**: Address security concerns related to code execution and data access, especially
when dealing with external codebases.
