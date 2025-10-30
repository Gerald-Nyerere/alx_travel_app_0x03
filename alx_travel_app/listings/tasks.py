from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_booking_confirmation_email(to_email, booking_id, destination):
    subject = "Booking Confirmation"
    message = f"Dear traveler,\n\nYour booking (ID: {booking_id}) for {destination} has been confirmed!\n\nThank you for choosing ALX Travel App."
    from_email = "noreply@alxtravel.com"
    
    send_mail(subject, message, from_email, [to_email])
    print(f"Confirmation email sent to {to_email}")
