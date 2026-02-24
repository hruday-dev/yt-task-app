import os
import json
import re
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# --- CONFIGURATION ---
# PASTE YOUR KEY HERE

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# --- SERVER-SIDE VIDEO SEARCH ---
def get_youtube_video_id(query):
    """
    Searches YouTube from the SERVER and returns the first Video ID.
    """
    try:
        # Force English results
        query = query + " full tutorial in English"
        encoded_query = query.replace(' ', '+')
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(url, headers=headers)
        
        # Extract ID using Regex
        video_ids = re.findall(r'"videoId":"(.*?)"', response.text)
        
        if video_ids:
            return video_ids[0] # Return the specific ID (e.g. "dQw4w9WgXcQ")
        return None
    except Exception as e:
        print(f"Server Search Error: {e}")
        return None

def generate_plan_from_groq(goal, days):
    print(f"⚡ Analyzing: {goal} for {days} days...")

    system_prompt = f"""
    You are an expert Professor. Create a {days}-Day Mastery Schedule for: "{goal}".
    
    CONSTRAINTS:
    1. Generate exactly {days} distinct items.
    2. SUMMARY: Write a COMPLETE, STANDALONE LESSON (250 words). Teach the topic directly.
    3. VIDEO QUERY: Provide a specific search term for a long-form tutorial (10min+).
    
    Output format (JSON):
    {{
        "tasks": [
            {{
                "day": 1,
                "title": "Topic Name",
                "summary": "Full lesson text...",
                "duration": "3 Hours",
                "youtube_query": "Topic Name deep dive tutorial",
                "web_queries": ["docs"],
                "category": "Learning",
                "icon": "BOOK",
                "color": "blue"
            }}
        ]
    }}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create the {days}-day plan."}
            ],
            temperature=0.3,
            max_tokens=8000, 
            response_format={"type": "json_object"}
        )

        data = json.loads(completion.choices[0].message.content)
        tasks = data.get("tasks", [])

        # --- POST-PROCESSING: SELECT VIDEOS ON SERVER ---
        print("🔍 Server is selecting videos for all tasks...")
        for task in tasks:
            # 1. Get Query
            query = task.get("youtube_query", task['title'])
            
            # 2. Perform Selection on Server
            video_id = get_youtube_video_id(query)
            
            # 3. Attach ID to the task data
            if video_id:
                task['video_id'] = video_id
                task['video_url'] = f"https://www.youtube.com/watch?v={video_id}"
            else:
                task['video_id'] = None
                
            # Defaults
            if 'duration' not in task: task['duration'] = "3 Hours"

        return tasks

    except Exception as e:
        print(f"❌ Groq API Error: {e}")
        return []

@app.route('/analyze_goal', methods=['POST'])
def analyze_goal():
    data = request.json
    tasks = generate_plan_from_groq(data.get('goal'), data.get('days', 5))
    return jsonify({"tasks": tasks})

if __name__ == '__main__':
    print("🚀 Server running on port 4000...")
    app.run(host='0.0.0.0', port=4000)
