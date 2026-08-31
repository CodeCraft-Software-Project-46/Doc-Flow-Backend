
from django.core.mail import send_mail

def send_user_credentials(user,temp_password, is_reset=False):
    send_mail(
        subject= "Your Account Details",
        message=f"""
        Hello,

        Your account has been created.

        Username: {user.username}
        Temporary Password: {temp_password}

        login to the system:
        {"http://localhost:5173/"}
        """,
        from_email="caftcode@gmail.com",
        recipient_list=[user.email],
    )

