# OER AI Agent Demo

This is a demo package of the OER AI Agent. It finds open educational resources for courses. No API key is required. Everything runs on your computer using built-in suggestions and web scraping.

What is in this package

1. A web application you can run in your browser
2. A command-line test you can run to check that everything works
3. Code that searches for OER and scores them by quality

How to get started

1. Install Python if you do not have it. Get it from python.org. When you install, check the box that says "Add Python to PATH".
2. Open Command Prompt or PowerShell. Go to the demo folder.
3. Install the required packages. Type: pip install -r requirements.txt
4. Run the test. Double-click TEST_AGENT.bat or type: python test_simple.py
5. Optional: Start the web app. Double-click start.bat or type: python app.py. Then open http://localhost:5000 in your browser.

No API key needed

The .env file is already in this folder. It is set up so the program does not call any external API. You do not need to sign up for OpenAI or any other service. The program uses built-in rules and suggestions instead.

What works without an API

- Finding course-related OER from built-in suggestions
- Quality scores for each resource
- The web interface to search by course code
- All main features

Files you can read

- START_HERE.md: Short list of steps to run the demo
- INSTRUCTIONS.md: Step-by-step instructions with numbering and troubleshooting

If something goes wrong

- If Python is not recognized: Install Python and make sure "Add to PATH" was checked.
- If pip is not recognized: Try typing python -m pip install -r requirements.txt
- If you see ModuleNotFoundError: Run pip install -r requirements.txt again
