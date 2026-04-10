# Instructions for the OER AI Agent Demo

Plain step-by-step instructions. No API key required.

1. What you need

- A computer with Windows, Mac, or Linux
- Python 3.8 or newer
- An internet connection (only for installing packages and for the web app)

2. Install Python

2.1. Go to https://www.python.org/downloads/
2.2. Download the latest Python 3 for your system.
2.3. Run the installer.
2.4. On the first screen, check the box that says "Add Python to PATH".
2.5. Click Install Now and wait for it to finish.
2.6. To confirm: open Command Prompt (or Terminal on Mac/Linux) and type python --version. You should see something like Python 3.12.0.

3. Open Command Prompt in the demo folder

3.1. Press the Windows key and type cmd, then press Enter (or use PowerShell).
3.2. Type cd and a space, then drag the demo folder into the window and press Enter. Or type the path by hand, for example: cd C:\Users\YourName\Documents\Cursor\demo
3.3. Press Enter. The prompt should now show that you are in the demo folder.

4. Install the required packages

4.1. Type: pip install -r requirements.txt
4.2. Press Enter.
4.3. Wait until all packages are installed. This can take two to five minutes.
4.4. If you see an error that pip is not recognized, try: python -m pip install -r requirements.txt

5. Run the test

5.1. Double-click TEST_AGENT.bat in the demo folder, or
5.2. In Command Prompt type: python test_simple.py and press Enter.
5.3. The test will check your setup and then run a sample course search.
5.4. You should see a line like "Resources Found" and "Resources Evaluated". That means the demo is working.

6. Optional: Start the web interface

6.1. Double-click start.bat, or in Command Prompt type: python app.py
6.2. Wait until you see a message like "Running on http://127.0.0.1:5000".
6.3. Open your web browser and go to: http://localhost:5000
6.4. In the search box, enter a course code (for example ENGL 1101 or ITEC 1001).
6.5. Click the button to search. Results will show a list of OER with quality scores.

7. No API key needed

- The demo folder already contains a .env file.
- The .env file is set so that no external API is used.
- You do not need to create an account with OpenAI or any other service.
- The program uses built-in suggestions and rules only.

8. Troubleshooting

8.1. "Python is not recognized"
- Install Python from python.org and make sure you checked "Add Python to PATH" during installation.

8.2. "pip is not recognized"
- Use: python -m pip install -r requirements.txt

8.3. "ModuleNotFoundError" when running the test
- Run: pip install -r requirements.txt again from the demo folder.

8.4. "Port 5000 already in use"
- Another program is using port 5000. Close that program or restart your computer, then run start.bat again.

8.5. No results or an error during search
- The demo can still show default suggestions. If the test completed without a crash, the setup is correct. You can try a different course code in the web interface.

9. What works in this demo

- Running the test script (TEST_AGENT.bat or python test_simple.py)
- Starting the web app (start.bat or python app.py)
- Searching by course code and seeing OER suggestions with scores
- No sign-up and no API key required

10. Next steps

- Try different course codes in the web interface.
- Read README.md for a short overview.
- Use START_HERE.md for a quick list of steps.
