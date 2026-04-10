# Start Here

This demo runs without any API key. Follow these steps in order.

Step 1: Install Python

- If you do not have Python, download it from python.org
- During setup, check the box "Add Python to PATH"
- To check: open Command Prompt and type python --version. You should see a version number.

Step 2: Go to this folder in Command Prompt

- Open Command Prompt (or PowerShell)
- Type: cd then a space, then the full path to this demo folder
- Example: cd C:\Users\YourName\Documents\Cursor\demo
- Press Enter

Step 3: Install packages

- Type: pip install -r requirements.txt
- Press Enter
- Wait until it finishes (a few minutes is normal)

Step 4: Run the test

- Double-click TEST_AGENT.bat
- Or in Command Prompt type: python test_simple.py
- You should see test results with resources found.

Step 5: Optional – run the web interface

- Double-click start.bat
- Or type: python app.py
- Open your browser and go to: http://localhost:5000
- Enter a course code (for example ITEC 1001) and click Search.

No API key is needed. The .env file is already set for no-API mode. You can start as soon as Python and the packages are installed.

For more detail and troubleshooting, see INSTRUCTIONS.md.
