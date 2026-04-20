from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import WorkingHoursConfig
from .serializers import WorkingHoursSerializer

# ======================================================
# GET CONFIG
# ======================================================
@api_view(['GET']) #This function ONLY accepts GET requests"
def get_config(request):
    config = WorkingHoursConfig.objects.first() #fetch data from DB It takes ONE full row (first record)  Only ONE config for whole company
    print(config)
    print("*")
    if not config:
        return Response(
            {"message": "No working hours found"},
            status=status.HTTP_200_OK
        )
    
    serializer = WorkingHoursSerializer(config) #converts Python object → JSON
    #print(serializer)
    print("*")
    print(serializer.data)
    print("*")
    return Response(serializer.data, status=status.HTTP_200_OK) #send to frontend

# ======================================================
# SAVE / UPDATE CONFIG
# ======================================================
@api_view(['POST'])
def save_config(request):
    print(request)
    print(request.data) #data from frontend
    config = WorkingHoursConfig.objects.first()

    # If config exists → update it
    if config:
        serializer = WorkingHoursSerializer(config, data=request.data)
    else:
        # If not exists → create new row
        serializer = WorkingHoursSerializer(data=request.data)

    if serializer.is_valid():#validate data
        serializer.save() #save to database

        return Response(
            {
                "message": "Working hours configuration saved successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    return Response(
        {
            "message": "Validation failed",
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )