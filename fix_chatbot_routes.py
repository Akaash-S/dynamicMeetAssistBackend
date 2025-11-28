"""
Quick script to fix all chatbot routes to use request.current_user
"""

import re

# Read the file
with open('routes/chatbot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all function signatures
content = re.sub(
    r'def (send_voice_message|get_history|clear_history|get_voice_status|index_user_data)\(current_user\):',
    r'def \1():',
    content
)

# Add current_user = request.current_user after each try: for these functions
functions_to_fix = [
    'send_voice_message',
    'get_history',
    'clear_history',
    'get_voice_status',
    'index_user_data'
]

for func in functions_to_fix:
    # Find the function and add current_user line after try:
    pattern = rf'(def {func}\(\):.*?try:)'
    replacement = r'\1\n        current_user = request.current_user'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('routes/chatbot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed all chatbot routes!")
