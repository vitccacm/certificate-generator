"""
Simple Math CAPTCHA Utilities
Generates simple math questions for verification.
No image dependencies required.
"""
import random
from flask import session


def generate_math_captcha():
    """
    Generate a simple math CAPTCHA question.
    Returns a tuple of (question_text, answer).
    """
    operations = [
        ('add', '+'),
        ('subtract', '-'),
        ('multiply', '×'),
    ]
    
    op_name, op_symbol = random.choice(operations)
    
    if op_name == 'add':
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        answer = a + b
    elif op_name == 'subtract':
        a = random.randint(10, 30)
        b = random.randint(1, a)  # Ensure positive result
        answer = a - b
    else:  # multiply
        a = random.randint(2, 10)
        b = random.randint(2, 10)
        answer = a * b
    
    question = f"{a} {op_symbol} {b} = ?"
    return question, answer


def get_captcha_question():
    """
    Generate a new CAPTCHA question and store answer in session.
    Returns the question text.
    """
    question, answer = generate_math_captcha()
    session['captcha_answer'] = str(answer)
    return question


def validate_captcha(user_input):
    """
    Validate user's CAPTCHA answer against the stored answer.
    Returns True if valid, False otherwise.
    Clears the CAPTCHA after validation attempt.
    """
    if not user_input:
        return False
    
    stored_answer = session.get('captcha_answer', '')
    
    # Clear CAPTCHA after attempt (one-time use)
    session.pop('captcha_answer', None)
    
    # Compare as strings (strip whitespace)
    user_answer = str(user_input).strip()
    
    return user_answer == stored_answer
