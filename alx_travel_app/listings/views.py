import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


class InitiatePaymentView(APIView):
    def post(self, request):
        try:
            booking_ref = request.data.get("booking_reference")
            amount = request.data.get("amount")
            email = request.data.get("email")

            if not all([booking_ref, amount, email]):
                return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)

            # Create payment entry
            payment = Payment.objects.create(
                booking_reference=booking_ref,
                amount=amount,
                status="Pending"
            )

            # Chapa API payload
            payload = {
                "amount": amount,
                "currency": "ETB",
                "email": email,
                "tx_ref": booking_ref,
                "callback_url": "https://your-domain.com/api/verify-payment/",
                "return_url": "https://your-frontend.com/payment-success",
                "customization[title]": "Booking Payment",
                "customization[description]": "Payment for booking confirmation"
            }

            headers = {
                "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
            }

            response = requests.post(
                f"{settings.CHAPA_BASE_URL}/transaction/initialize",
                headers=headers,
                data=payload
            )

            chapa_data = response.json()

            if chapa_data.get("status") == "success":
                payment.transaction_id = chapa_data["data"]["tx_ref"]
                payment.save()
                return Response(chapa_data, status=status.HTTP_200_OK)

            return Response(chapa_data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPaymentView(APIView):
    def get(self, request, tx_ref):
        try:
            headers = {
                "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
            }

            response = requests.get(
                f"{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}",
                headers=headers
            )

            chapa_data = response.json()
            payment = Payment.objects.get(booking_reference=tx_ref)

            if chapa_data.get("status") == "success" and chapa_data["data"]["status"] == "success":
                payment.status = "Completed"
            else:
                payment.status = "Failed"

            payment.save()
            return Response({
                "booking_reference": tx_ref,
                "payment_status": payment.status,
                "chapa_response": chapa_data
            }, status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
