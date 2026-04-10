# Package Contents

This document lists what is in the demo folder. Plain list, no images.

1. Main program files

- app.py: Web application. Run with python app.py or start.bat.
- oer_agent.py: Core logic that finds and evaluates OER.
- config.py: Settings. Reads from .env.
- cli.py: Command-line interface if you want to run from the terminal.

2. Configuration

- .env: Already set for no-API mode. Do not add a key unless you want to use an API later.
- requirements.txt: List of Python packages to install with pip.

3. Scripts to run

- start.bat: Starts the web app. Double-click or run from Command Prompt.
- TEST_AGENT.bat: Runs a short test. Double-click or run from Command Prompt.
- test_simple.py: Same test as TEST_AGENT.bat, run with python test_simple.py.
- test_courses.py: Tests several courses. Run with python test_courses.py.

4. Documentation (all plain text, no images, no bold)

- README.md: Overview and quick start.
- START_HERE.md: Short list of steps to run the demo.
- INSTRUCTIONS.md: Full step-by-step instructions with numbering and troubleshooting.
- PACKAGE_INFO.md: This file.

5. Folders

- scrapers: Code that gets data from syllabus and OER sites.
- llm: Code that can use an API if you add a key; in this demo it runs without a key.
- evaluators: Code that scores OER quality and checks licenses.
- utils: Helper code for logging and paths.
- templates: HTML for the web interface.
- static: CSS and JavaScript for the web interface.

No API is required. Install Python, run pip install -r requirements.txt, then run TEST_AGENT.bat or start.bat.
