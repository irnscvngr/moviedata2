@echo off
cd /d "C:\Users\patri\OneDrive\Data Science\Practices\26.08.21 - MovieData2"
call "C:\Users\patri\anaconda3\Scripts\activate.bat" bigdata
streamlit run app/main.py
pause