import uuid

def generate_user_email_and_password_fn(name, surname):
    email = f"{name.lower()}.{surname.lower()}@eimzo.local"
    password = str(uuid.uuid4())
    return {"email": email, "password": password}